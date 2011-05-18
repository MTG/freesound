from __future__ import with_statement
from gaia_wrapper import *
from threading import Lock
from shared_lock import SharedLock
import time, os
import simplejson as json
from settings import PRESETS
from logger import logger

UPDATE_TIMEOUT = 1
READ_TIMEOUT   = 1

class GaiaIndexer:

    def __init__(self):
        self.lock = Lock()
        self.shared_lock = SharedLock()
        self.index = GaiaWrapper()
        logger.debug('Initialized GaiaIndexer')


    def __acquire_shared(self, timeout=READ_TIMEOUT):
        acquired = self.shared_lock.acquire_shared(timeout)
        return True if acquired else self.raise_locked()


    def __release_shared(self):
        self.shared_lock.release_shared()


    def __acquire_exclusive(self, timeout=UPDATE_TIMEOUT):
        acquired = self.shared_lock.acquire(timeout)
        return True if acquired else self.raise_locked()


    def __release_exclusive(self):
        self.shared_lock.release()


    def __raise_locked(self):
        raise Exception('The index is currently locked which probably means it is being updated.')


    def add_point(self, yaml_path, sound_id):
        try:
            self.__acquire_exclusive(None)
            self.index.add_point(yaml_path, sound_id)
        finally:
            self.__release_exclusive()


    def delete_point(self, sound_id):
        try:
            self.__acquire_exclusive(None)
            self.index.delete_point(sound_id)
        finally:
            self.__release_exclusive()


    def search_index(self, point, no_of_results, presetkey):
        '''
        The 'point' argument can either be the name of an already present point
        or the location of a yaml file (has to have extension .yaml).
        '''
        self.__acquire_shared()
        try:
            return self.index.search_dataset(point, no_of_results, presetkey)
        finally:
            self.__release_shared(index)
