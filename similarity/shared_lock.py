#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
###############################################################################
#
# Shared lock (aka reader-writer lock) implementation.
#
# Written by Dmitry Dvoinikov <dmitry@targeted.org>
# Distributed under MIT license.
#
# The latest source code (complete with self-tests) is available from:
# http://www.targeted.org/python/recipes/shared_lock.py
#
# Requires exc_string module available from either
# http://www.targeted.org/python/recipes/exc_string.py -OR-
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/444746
#
# Features:
#
# 1. Supports timeouts. Attempts to acquire a lock occassionally time out in
#    a specified amount of time.
# 2. Fully reentrant - single thread can have any number of both shared and
#    exclusive ownerships on the same lock instance (restricted with the lock 
#    semantics of course).
# 3. Supports FIFO order for threads waiting to acquire the lock exclusively.
# 4. Robust and manageable. Can be created in debug mode so that each lock
#    operation causes the internal invariant to be checked (although this 
#    certainly slows it down). Can be created with logging so that each lock
#    operation is verbosely logged.
# 5. Prevents either side from starvation by picking the winning thread at
#    random if such behaviour is appropriate.
# 6. Recycles temporary one-time synchronization objects.
# 7. Can be used as a drop-in replacement for threading.Lock, ex.
#    >> from shared_lock import SharedLock as Lock
#    because the semantics and exclusive locking interface are identical to 
#    that of threading.Lock.
#
# Synopsis:
#
# class SharedLock(object):
#     def acquire(timeout_sec = None):
#         Attempts to acquire the lock exclusively within the optional timeout.
#         If the timeout is not specified, waits for the lock infinitely.
#         Returns True if the lock has been acquired, False otherwise.
#     def release():
#         Releases the lock previously locked by a call to acquire().
#         Returns None.
#     def acquire_shared(timeout_sec = None):
#         Attempts to acquire the lock in shared mode within the optional
#         timeout. If the timeout is not specified, waits for the lock 
#         infinitely. Returns True if the lock has been acquired, False 
#         otherwise.
#     def release_shared():
#         Releases the lock previously locked by a call to acquire_shared().
#         Returns None.
#
################################################################################
#
# (c) 2005 Dmitry Dvoinikov <dmitry@targeted.org>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy 
# of this software and associated documentation files (the "Software"), to deal 
# in the Software without restriction, including without limitation the rights to 
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies 
# of the Software, and to permit persons to whom the Software is furnished to do 
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, 
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN 
# THE SOFTWARE.
#
################################################################################

__all__ = [ "SharedLock" ]

################################################################################

from threading import Lock, currentThread, Event
from random import randint
from exc_string import trace_string

if not hasattr(__builtins__, "sorted"):
    def sorted(seq):
        result = [ x for x in seq ]
        result.sort()
        return result

################################################################################

class SharedLock(object):

    def __init__(self, log = None, debug = False):
        """
        Takes two optional parameters, (1) log is an external log function the
        lock would use to send its messages to, ex: lambda s: xprint(s),
        (2) debug is a boolean value, if it's True the lock would be checking
        its internal invariant before and after each call.
        """

        self.__log, self.__debug, self.lckLock = log, debug, Lock()
        self.thrOwner, self.intOwnerDepth, self.dicUsers = None, 0, {}
        self.lstOwners, self.lstUsers, self.lstPooledEvents = [], [], []

    ################################### utility log function

    def _log(self, s):
        thrCurrent = currentThread()
        self.__log("%s @ %.08x %s %s @ %.08x in %s" 
                  % (thrCurrent.getName(), id(thrCurrent), s, 
                     self._debug_dump(), id(self), trace_string()))

    ################################### debugging lock state dump

    def _debug_dump(self):
        return "SharedLock(Ex:[%s] (%s), Sh:[%s] (%s))" \
               % (self.thrOwner is not None 
                  and "%s:%d" % (self.thrOwner.getName(), 
                                 self.intOwnerDepth)
                  or "",
                  ", ".join([ "%s:%d" % (th.getName(), dp)
                              for th, evt, dp in self.lstOwners ]),
                  ", ".join(sorted([ "%s:%d" % (th.getName(), dp)
                                   for th, dp in self.dicUsers.iteritems() ])),
                  ", ".join([ "%s:%d" % (th.getName(), dp)
                              for th, evt, dp in self.lstUsers ]))

    def debug_dump(self):
        """
        Returns a printable string describing the current lock state.
        """

        self._lock()
        try:
            return self._debug_dump()
        finally:
            self._unlock()

    ################################### utility predicates

    def _has_owner(self):
        return self.thrOwner is not None

    def _has_pending_owners(self):
        return len(self.lstOwners) > 0
    
    def _has_users(self):
        return len(self.dicUsers) > 0

    def _has_pending_users(self):
        return len(self.lstUsers) > 0

    ################################### lock invariant

    def _invariant(self): # invariant checks slow down the lock a lot (~3 times)

        # a single thread can hold both shared and exclusive lock
        # as soon as it's the only thread holding either

        if self._has_owner() and self._has_users() \
        and self.dicUsers.keys() != [self.thrOwner]:
            return False

        # if noone is holding the lock, noone should be pending on it

        if not self._has_owner() and not self._has_users():
            return not self._has_pending_owners() \
            and not self._has_pending_users()

        # noone can be holding a lock zero times and vice versa

        if (self._has_owner() and self.intOwnerDepth <= 0) \
        or (not self._has_owner() and self.intOwnerDepth > 0):
            return False

        if len(filter(lambda dp: dp <= 0, self.dicUsers.values())) > 0:
            return False

        # if there is no owner nor pending owners, there should be no
        # pending users (all users must be executing)

        if not self._has_owner() and not self._has_pending_owners() \
        and self._has_pending_users():
            return False

        # if there is no owner nor running users, there should be no
        # pending owners (an owner must be executing)

        if not self._has_owner() and not self._has_users() \
        and self._has_pending_owners():
            return False

        # a thread may be pending on a lock only once, either as user or as owner

        lstPendingThreads = sorted(map(lambda t: t[0], self.lstUsers) + 
                                   map(lambda t: t[0], self.lstOwners))

        for i in range(len(lstPendingThreads) - 1):
            if lstPendingThreads[i] is lstPendingThreads[i+1]:
                return False

        return True 

    ################################### instance lock

    def _lock(self):
        self.lckLock.acquire()

    def _unlock(self):
        self.lckLock.release()

    ################################### sleep/wakeup event pool

    def _pick_event(self):                      # events are pooled/recycled
        if len(self.lstPooledEvents):           # because creating and then
            return self.lstPooledEvents.pop(0)  # garbage collecting kernel
        else:                                   # objects on each call could
            return Event()                      # be prohibitively expensive

    def _unpick_event(self, _evtEvent):
        self.lstPooledEvents.append(_evtEvent)

    ################################### sleep/wakeup utility

    def _acquire_event(self, _evtEvent, timeout): # puts the thread to sleep until the
                                                  # lock is acquired or timeout elapses

        if timeout is None:
            _evtEvent.wait()
            result = True
        else:
            _evtEvent.wait(timeout)
            result = _evtEvent.isSet()

        thrCurrent = currentThread()

        self._lock()
        try:

            # even if result indicates failure, the thread might still be having
            # the lock (race condition between the isSet() and _lock() above)

            if not result:
                result = _evtEvent.isSet()

            # if the lock has not been acquired, the thread must be removed from
            # the pending list it's on. in case the thread was waiting for the
            # exclusive lock and it previously had shared locks, it's put to sleep
            # again this time infinitely (!), waiting for its shared locks back

            boolReAcquireShared = False

            if not result: # the thread has failed to acquire the lock
                
                for i, (thrUser, evtEvent, intSharedDepth) in enumerate(self.lstUsers):
                    if thrUser is thrCurrent and evtEvent is _evtEvent:
                        assert intSharedDepth == 1
                        del self.lstUsers[i]
                        break
                else:
                    for i, (thrOwner, evtEvent, intSharedDepth) in enumerate(self.lstOwners):
                        if thrOwner is thrCurrent and evtEvent is _evtEvent:
                            del self.lstOwners[i]
                            if intSharedDepth > 0:
                                if not self._has_owner():
                                    self.dicUsers[thrCurrent] = intSharedDepth
                                else:
                                    self.lstUsers.append((thrCurrent, _evtEvent, intSharedDepth))
                                    boolReAcquireShared = True
                            break
                    else:
                        assert False, "Invalid thread for %s in %s" % \
                                      (self._debug_dump(), trace_string())

                # if a thread has failed to acquire a lock, it's identical as if it had
                # it and then released, therefore other threads should be released now

                self._release_threads()

            if not boolReAcquireShared:
                _evtEvent.clear()
                self._unpick_event(_evtEvent)

            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), trace_string())

            if result:
                if self.__log: self._log("acquired")
            else:
                if self.__log: self._log("timed out in %.02f second(s) waiting for" % timeout)
                if boolReAcquireShared:
                    if self.__log: self._log("acquiring %d previously owned shared lock(s) for" % intSharedDepth)

        finally:
            self._unlock()

        if boolReAcquireShared:
            assert self._acquire_event(_evtEvent, None)
            return False

        return result

    def _release_events(self, _lstEvents): # releases waiting thread(s) 

        for evtEvent in _lstEvents:
            evtEvent.set() 

    ################################### exclusive acquire

    def acquire(self, timeout = None):
        """
        Attempts to acquire the lock exclusively within the optional timeout.
        If the timeout is not specified, waits for the lock infinitely.
        Returns True if the lock has been acquired, False otherwise.
        """

        thrCurrent = currentThread()

        self._lock()
        try:

            if self.__log: self._log("acquiring exclusive")
            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), trace_string())

            # this thread already has exclusive lock, the count is incremented

            if thrCurrent is self.thrOwner:

                self.intOwnerDepth += 1
                if self.__debug:
                    assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                              (self._debug_dump(), trace_string())
                if self.__log: self._log("acquired exclusive")
                return True

            # this thread already has shared lock, this is the most complicated case

            elif thrCurrent in self.dicUsers:
                
                # the thread gets exclusive lock immediately if there is no other threads

                if self.dicUsers.keys() == [thrCurrent] \
                and not self._has_pending_users() and not self._has_pending_owners():
                    
                    self.thrOwner = thrCurrent
                    self.intOwnerDepth = 1
                    if self.__debug:
                        assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                                  (self._debug_dump(), trace_string())
                    if self.__log: self._log("acquired exclusive")
                    return True

                # the thread releases its shared lock in hope for the future
                # exclusive one

                intSharedDepth = self.dicUsers.pop(thrCurrent) # that many times it had shared lock

                evtEvent = self._pick_event()
                self.lstOwners.append((thrCurrent, evtEvent, intSharedDepth)) # it will be given them back

                self._release_threads()

            # a thread acquires exclusive lock whenever there is no
            # current owner nor running users

            elif not self._has_owner() and not self._has_users():

                self.thrOwner = thrCurrent
                self.intOwnerDepth = 1
                if self.__debug:
                    assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                              (self._debug_dump(), trace_string())
                if self.__log: self._log("acquired exclusive")
                return True

            # otherwise the thread registers itself as a pending owner with no
            # prior record of holding shared lock

            else: 

                evtEvent = self._pick_event()
                self.lstOwners.append((thrCurrent, evtEvent, 0))

            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), trace_string())
            if self.__log: self._log("waiting for exclusive")

        finally:
            self._unlock()

        return self._acquire_event(evtEvent, timeout) # the thread waits for a lock release

    ################################### shared acquire

    def acquire_shared(self, timeout = None):
        """
        Attempts to acquire the lock in shared mode within the optional 
        timeout. If the timeout is not specified, waits for the lock
        infinitely. Returns True if the lock has been acquired, False
        otherwise.
        """

        thrCurrent = currentThread()

        self._lock()
        try:

            if self.__log: self._log("acquiring shared")
            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), trace_string())

            # this thread already has shared lock, the count is incremented

            if thrCurrent in self.dicUsers: 
                self.dicUsers[thrCurrent] += 1
                if self.__debug:
                    assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                              (self._debug_dump(), trace_string())
                if self.__log: self._log("acquired shared")
                return True

            # this thread already has exclusive lock, now it also has shared

            elif thrCurrent is self.thrOwner: 
                if thrCurrent in self.dicUsers:
                    self.dicUsers[thrCurrent] += 1
                else:
                    self.dicUsers[thrCurrent] = 1
                if self.__debug:
                    assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                              (self._debug_dump(), trace_string())
                if self.__log: self._log("acquired shared")
                return True

            # a thread acquires shared lock whenever there is no owner
            # nor pending owners (to prevent owners starvation)

            elif not self._has_owner() and not self._has_pending_owners():
                self.dicUsers[thrCurrent] = 1
                if self.__debug:
                    assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                              (self._debug_dump(), trace_string())
                if self.__log: self._log("acquired shared")
                return True

            # otherwise the thread registers itself as a pending user

            else:

                evtEvent = self._pick_event()
                self.lstUsers.append((thrCurrent, evtEvent, 1))

            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), trace_string())
            if self.__log: self._log("waiting for shared")

        finally:
            self._unlock()

        return self._acquire_event(evtEvent, timeout) # the thread waits for a lock release

    ################################### 

    def _release_threads(self):

        # a decision is made which thread(s) to awake upon a release

        if self._has_owner():
            boolWakeUpOwner = False # noone to awake, the exclusive owner
            boolWakeUpUsers = False # must've released its shared lock
        elif not self._has_pending_owners():
            boolWakeUpOwner = False
            boolWakeUpUsers = self._has_pending_users()
        elif not self._has_users():
            boolWakeUpOwner = not self._has_pending_users() \
                              or randint(0, 1) == 0 # this prevents starvation
            boolWakeUpUsers = self._has_pending_users() and not boolWakeUpOwner
        else:
            boolWakeUpOwner = False # noone to awake, running users prevent
            boolWakeUpUsers = False # pending owners from running

        # the winning thread(s) are released

        lstEvents = []

        if boolWakeUpOwner:
            self.thrOwner, evtEvent, intSharedDepth = self.lstOwners.pop(0)
            self.intOwnerDepth = 1
            if intSharedDepth > 0:
                self.dicUsers[self.thrOwner] = intSharedDepth # restore thread's shared locks
            lstEvents.append(evtEvent)
        elif boolWakeUpUsers:
            for thrUser, evtEvent, intSharedDepth in self.lstUsers:
                self.dicUsers[thrUser] = intSharedDepth
                lstEvents.append(evtEvent)
            del self.lstUsers[:]

        self._release_events(lstEvents)

    ################################### exclusive release

    def release(self):
        """
        Releases the lock previously locked by a call to acquire().
        Returns None.
        """

        thrCurrent = currentThread()

        self._lock()
        try:

            if self.__log: self._log("releasing exclusive")
            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), trace_string())

            if thrCurrent is not self.thrOwner:
                raise Exception("Current thread has not acquired the lock")

            # the thread releases its exclusive lock

            self.intOwnerDepth -= 1
            if self.intOwnerDepth > 0:
                if self.__debug:
                    assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                              (self._debug_dump(), trace_string())
                if self.__log: self._log("released exclusive")
                return

            self.thrOwner = None

            # a decision is made which pending thread(s) to awake (if any)

            self._release_threads()
            
            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), trace_string())
            if self.__log: self._log("released exclusive")

        finally:
            self._unlock()

    ################################### shared release

    def release_shared(self):
        """
        Releases the lock previously locked by a call to acquire_shared().
        Returns None.
        """

        thrCurrent = currentThread()

        self._lock()
        try:

            if self.__log: self._log("releasing shared")
            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), trace_string())

            if thrCurrent not in self.dicUsers:
                raise Exception("Current thread has not acquired the lock")
                
            # the thread releases its shared lock

            self.dicUsers[thrCurrent] -= 1
            if self.dicUsers[thrCurrent] > 0:
                if self.__debug:
                    assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                              (self._debug_dump(), trace_string())
                if self.__log: self._log("released shared")
                return
            else:
                del self.dicUsers[thrCurrent]

            # a decision is made which pending thread(s) to awake (if any)

            self._release_threads()
            
            if self.__debug:
                assert self._invariant(), "SharedLock invariant failed: %s in %s" % \
                                          (self._debug_dump(), trace_string())
            if self.__log: self._log("released shared")

        finally:
            self._unlock()

################################################################################

if __name__ == "__main__":
    
    print "self-testing module shared_lock.py:"

    from threading import Thread
    from time import sleep, time
    from random import random
    from math import log10

    log_lock = Lock()
    def log(s):
        log_lock.acquire()
        try:
            print s
        finally:
            log_lock.release()

    def deadlocks(f, t):
        th = Thread(target = f)
        th.setName("Thread")
        th.setDaemon(1)
        th.start()
        th.join(t)
        return th.isAlive()

    def threads(n, *f):
        start = time()
        evt = Event()
        ths = [ Thread(target = f[i % len(f)], args = (evt, )) for i in range(n) ]
        for i, th in enumerate(ths):
            th.setDaemon(1)
            th.setName(f[i % len(f)].__name__)
            th.start()
        evt.set()
        for th in ths:
            th.join()
        return time() - start

    # simple test

    print "simple test:",

    currentThread().setName("MainThread")

    lck = SharedLock(None, True)
    assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"

    assert lck.acquire()
    assert lck.debug_dump() == "SharedLock(Ex:[MainThread:1] (), Sh:[] ())"
    lck.release()
    assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"

    assert lck.acquire_shared()
    assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[MainThread:1] ())"
    lck.release_shared()
    assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"

    try:
        lck.release()
    except Exception, e:
        assert str(e) == "Current thread has not acquired the lock"
    else:
        assert False

    try:
        lck.release_shared()
    except Exception, e:
        assert str(e) == "Current thread has not acquired the lock"
    else:
        assert False

    print "ok"

    # recursion test

    print "recursive lock test:",

    lck = SharedLock(None, True)

    assert lck.acquire()
    assert lck.acquire()
    assert lck.debug_dump() == "SharedLock(Ex:[MainThread:2] (), Sh:[] ())"
    lck.release()
    assert lck.debug_dump() == "SharedLock(Ex:[MainThread:1] (), Sh:[] ())"
    lck.release()

    assert lck.acquire_shared()
    assert lck.acquire_shared()
    assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[MainThread:2] ())"
    lck.release_shared()
    assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[MainThread:1] ())"
    lck.release_shared()

    print "ok"

    # same thread shared/exclusive upgrade test

    print "same thread shared/exclusive upgrade test:",

    lck = SharedLock(None, True)

    def upgrade():

        # ex -> sh <- sh <- ex

        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"
        assert lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[Thread:1] (), Sh:[] ())"
        assert lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[Thread:1] (), Sh:[Thread:1] ())"
        lck.release_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[Thread:1] (), Sh:[] ())"
        lck.release()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"

        # ex -> sh <- ex <- sh

        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"
        assert lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[Thread:1] (), Sh:[] ())"
        assert lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[Thread:1] (), Sh:[Thread:1] ())"
        lck.release()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[Thread:1] ())"
        lck.release_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"

        # sh -> ex <- ex <- sh

        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"
        assert lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[Thread:1] ())"
        assert lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[Thread:1] (), Sh:[Thread:1] ())"
        lck.release()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[Thread:1] ())"
        lck.release_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"

        # sh -> ex <- sh <- ex

        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"
        assert lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[Thread:1] ())"
        assert lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[Thread:1] (), Sh:[Thread:1] ())"
        lck.release_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[Thread:1] (), Sh:[] ())"
        lck.release()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"

    assert not deadlocks(upgrade, 2.0)

    print "ok"

    # timeout test

    print "timeout test:",

    # exclusive/exclusive timeout

    lck = SharedLock(None, True)

    def f(evt):
        evt.wait()
        assert lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[f:1] (), Sh:[] ())"
        sleep(1.0)
        assert lck.debug_dump() == "SharedLock(Ex:[f:1] (g:0), Sh:[] ())"
        lck.release()

    def g(evt):
        evt.wait()
        sleep(0.5)
        assert lck.debug_dump() == "SharedLock(Ex:[f:1] (), Sh:[] ())"
        assert not lck.acquire(0.1)
        assert lck.debug_dump() == "SharedLock(Ex:[f:1] (), Sh:[] ())"
        assert lck.acquire(0.5)
        assert lck.debug_dump() == "SharedLock(Ex:[g:1] (), Sh:[] ())"
        lck.release()

    threads(2, f, g)

    # shared/shared no timeout

    lck = SharedLock(None, True)

    def f(evt):
        evt.wait()
        assert lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        sleep(1.0)
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        lck.release_shared()

    def g(evt):
        evt.wait()
        sleep(0.5)
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        assert lck.acquire_shared(0.1)
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1, g:1] ())"
        lck.release_shared()

    threads(2, f, g)

    # exclusive/shared timeout

    lck = SharedLock(None, True)

    def f(evt):
        evt.wait()
        assert lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[f:1] (), Sh:[] ())"
        sleep(1.0)
        assert lck.debug_dump() == "SharedLock(Ex:[f:1] (), Sh:[] (g:1))"
        lck.release()

    def g(evt):
        evt.wait()
        sleep(0.5)
        assert lck.debug_dump() == "SharedLock(Ex:[f:1] (), Sh:[] ())"
        assert not lck.acquire_shared(0.1)
        assert lck.debug_dump() == "SharedLock(Ex:[f:1] (), Sh:[] ())"
        assert lck.acquire_shared(0.5)
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[g:1] ())"
        lck.release_shared()

    threads(2, f, g)

    # shared/exclusive timeout

    lck = SharedLock(None, True)

    def f(evt):
        evt.wait()
        assert lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        sleep(1.0)
        assert lck.debug_dump() == "SharedLock(Ex:[] (g:0), Sh:[f:1] ())"
        lck.release_shared()

    def g(evt):
        evt.wait()
        sleep(0.5)
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        assert not lck.acquire(0.1)
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        assert lck.acquire(0.5)
        assert lck.debug_dump() == "SharedLock(Ex:[g:1] (), Sh:[] ())"
        lck.release()

    threads(2, f, g)

    # re-acquiring previously owned shared locks after an upgrade timeout

    lck = SharedLock(None, True)

    def f(evt):
        evt.wait()
        lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        sleep(1.0)
        start = time()
        assert not lck.acquire(0.1) # this locks for more than 0.1 sec.
        assert time() - start > 1.0
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"

    def g(evt):
        evt.wait()
        sleep(0.5)
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[g:1] (f:1), Sh:[] ())"
        sleep(1.1)
        lck.release()

    threads(2, f, g)

    print "ok"

    # different threads shared/exclusive upgrade test

    print "different threads shared/exclusive upgrade test:",

    lck = SharedLock(None, True)

    def f(evt):
        evt.wait()

        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[] ())"
        lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"

        sleep(3.0)

        lck.release_shared()

    def g(evt):
        evt.wait()
        
        sleep(1.0)
        
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1] ())"
        lck.acquire_shared()
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1, g:1] ())"

        sleep(3.0)

        assert lck.debug_dump() == "SharedLock(Ex:[] (h:0), Sh:[g:1] ())"
        lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[g:1] (), Sh:[g:1] ())"

        lck.release()
        lck.release_shared()

    def h(evt):
        evt.wait()
        
        sleep(2.0)
        
        assert lck.debug_dump() == "SharedLock(Ex:[] (), Sh:[f:1, g:1] ())"
        lck.acquire()
        assert lck.debug_dump() == "SharedLock(Ex:[h:1] (g:1), Sh:[] ())"

        sleep(1.0)

        lck.release()

    threads(3, f, g, h)

    print "ok"

    # different threads exclusive/exclusive deadlock test

    print "different threads exclusive/exclusive deadlock test:",

    lck = SharedLock(None, True)

    def deadlock(evt):
        lck.acquire()

    assert deadlocks(lambda: threads(2, deadlock), 2.0)

    print "ok"

    # different thread shared/exclusive deadlock test

    print "different threads shared/exclusive deadlock test:",

    lck = SharedLock(None, True)

    def deadlock1(evt):
        lck.acquire()

    def deadlock2(evt):
        lck.acquire_shared()

    assert deadlocks(lambda: threads(2, deadlock1, deadlock2), 2.0)

    print "ok"

    # different thread shared/shared deadlock test

    print "different threads shared/shared no deadlock test:",

    lck = SharedLock(None, True)

    def deadlock(evt):
        lck.acquire_shared()

    assert not deadlocks(lambda: threads(2, deadlock), 2.0)

    print "ok"

    # cross upgrade test

    print "different threads cross upgrade test:",

    lck = SharedLock(None, True)

    def cross(evt):
        lck.acquire_shared()
        sleep(1.0)
        lck.acquire()
        lck.release()
        lck.release_shared()

    assert not deadlocks(lambda: threads(2, cross), 2.0)

    print "ok"

    # exclusive interlock + timing test

    print "exclusive interlock + serialized timing test:",

    lck = SharedLock(None, True)
    val = 0

    def exclusive(evt):
        evt.wait()
        global val
        for i in range(10):
            lck.acquire()
            try:
                assert val == 0
                val += 1
                sleep(0.05 + random() * 0.05)
                assert val == 1
                val -= 1
                sleep(0.05 + random() * 0.05)
                assert val == 0
            finally:
                lck.release()

    assert threads(4, exclusive) > 0.05 * 2 * 10 * 4

    print "ok"

    # shared non-interlock timing test

    print "shared parallel timing test:",

    lck = SharedLock(None, True)

    def shared(evt):
        evt.wait()
        for i in range(10):
            lck.acquire_shared()
            try:
                sleep(0.1)
            finally:
                lck.release_shared()

    assert threads(10, shared) < 0.1 * 10 + 4.0

    print "ok"

    # shared/exclusive test

    print "multiple exclusive/shared threads busy loops:"

    lck, shlck = SharedLock(None, True), Lock()

    ex, sh, start, t = 0, 0, time(), 10.0
    
    def exclusive(evt):
        global ex, start, t
        evt.wait()
        i = 0
        while i % 100 != 0 or start + t > time():
            i += 1
            lck.acquire()
            try:
                ex += 1
            finally:
                lck.release()

    def shared(evt):
        global sh, start, t
        evt.wait()
        i = 0
        while i % 100 != 0 or start + t > time():
            i += 1
            lck.acquire_shared()
            try:
                shlck.acquire()
                try:
                    sh += 1
                finally:
                    shlck.release()
            finally:
                lck.release_shared()

    # even distribution

    print "2ex/2sh:",
    ex, sh, start = 0, 0, time()
    assert 10.0 < threads(4, exclusive, exclusive, shared, shared) < 12.0
    print "%d/%d:" % (ex, sh),
    assert abs(log10(float(ex) / float(sh))) < 1.3

    print "ok"

    # exclusive starvation

    print "1ex/3sh:",
    ex, sh, start = 0, 0, time()
    assert 10.0 < threads(4, exclusive, shared, shared, shared) < 12.0
    print "%d/%d:" % (ex, sh),
    assert abs(log10(float(ex) / float(sh))) < 1.3

    print "ok"

    # shared starvation

    print "3ex/1sh:",
    ex, sh, start = 0, 0, time()
    assert 10.0 < threads(4, exclusive, exclusive, exclusive, shared) < 12.0
    print "%d/%d:" % (ex, sh),
    assert abs(log10(float(ex) / float(sh))) < 1.3

    print "ok"

    # heavy threading test

    print "exhaustive threaded test (30 seconds):",

    lck = SharedLock(None, True)
    start, t = time(), 30.0
    
    def f(evt):
        global start, t
        evt.wait()
        while start + t > time():
    
            sleep(random() * 0.1)

            j = randint(0, 1)
            if j == 0: 
                jack = lck.acquire(*(randint(0, 1) == 0 and (random(), ) or ()))
            else:
                jack = lck.acquire_shared(*(randint(0, 1) == 0 and (random(), ) or ()))

            sleep(random() * 0.1)

            k = randint(0, 1)
            if k == 0: 
                kack = lck.acquire(*(randint(0, 1) == 0 and (random(), ) or ()))
            else:
                kack = lck.acquire_shared(*(randint(0, 1) == 0 and (random(), ) or ()))
            
            sleep(random() * 0.1)

            l = randint(0, 1)
            if l == 0: 
                lack = lck.acquire(*(randint(0, 1) == 0 and (random(), ) or ()))
            else:
                lack = lck.acquire_shared(*(randint(0, 1) == 0 and (random(), ) or ()))

            sleep(random() * 0.1)

            if lack:
                if l == 0: 
                    lck.release()
                else:
                    lck.release_shared()

            sleep(random() * 0.1)

            if kack:
                if k == 0: 
                    lck.release()
                else:
                    lck.release_shared()

            sleep(random() * 0.1)

            if jack:
                if j == 0: 
                    lck.release()
                else:
                    lck.release_shared()

    f0 = lambda evt: f(evt);
    f1 = lambda evt: f(evt);
    f2 = lambda evt: f(evt);
    f3 = lambda evt: f(evt);
    f4 = lambda evt: f(evt);
    f5 = lambda evt: f(evt);
    f6 = lambda evt: f(evt);
    f7 = lambda evt: f(evt);
    f8 = lambda evt: f(evt);
    f9 = lambda evt: f(evt);

    threads(10, f0, f1, f2, f3, f4, f5, f6, f7, f8, f9)

    print "ok"

    # specific anti-owners scenario (users cooperate by passing the lock
    # to each other to make owner starve to death)

    print "shareds cooperate in attempt to make exclusive starve to death:",

    lck, shlck, hold = SharedLock(None, True), Lock(), 0
    evtlock, stop = Event(), Event()

    def user(evt):
        
        evt.wait()
        
        try:

            while not stop.isSet():

                lck.acquire_shared()
                try:

                    evtlock.set()
                    
                    shlck.acquire()
                    try:
                        global hold
                        hold += 1
                    finally:
                        shlck.release()
                  
                    sleep(random() * 0.4)

                    waited = time()
                    while time() - waited < 3.0:
                        shlck.acquire()
                        try:
                            if hold > 1:
                                hold -= 1
                                break
                        finally:
                            shlck.release()

                    if time() - waited >= 3.0: # but in turn they lock themselves
                        raise Exception("didn't work")

                finally:
                    lck.release_shared()

                sleep(random() * 0.1)

        except Exception, e:
            assert str(e) == "didn't work"

    def owner(evt):
        evt.wait()
        evtlock.wait()
        lck.acquire()
        lck.release()
        stop.set()

    assert not deadlocks(lambda: threads(5, owner, user, user, user, user), 10.0)

    print "ok"

    print "benchmark:",

    lck, ii = SharedLock(), 0

    start = time()
    while time() - start < 5.0:
        for i in xrange(100):
            lck.acquire()
            lck.release()
            ii += 1

    print "%d empty lock/unlock cycles per second" % (ii / 5),

    print "ok"

    # all ok

    print "all ok"

################################################################################
# EOF
