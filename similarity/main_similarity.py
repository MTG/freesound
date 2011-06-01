import time, os, subprocess, signal, uuid, traceback, zmq, Queue, logging
from settings import REQREP_ADDRESS, NUM_THREADS
from threads import SimilarityThread
from gaia_indexer import GaiaIndexer

logger = logging.getLogger('similarity')

class SimilarityService():

    def __init__(self):
        logger.info('Initializing similarity service')
        self.num_threads = NUM_THREADS
        self.reqrep_address = REQREP_ADDRESS

    def stop(self):
        for x in xrange(self.num_threads):
            self.threads[x].stop()

    def wait_till_done(self):
        for x in xrange(self.num_threads):
            self.threads[x].join()

    def start(self):
        # first get the address to connect to from the DNS
        context = zmq.Context(1)

        worker_address = 'inproc://workers'
        logger.info("Binding workers' socket to %s" % worker_address)
        workers = context.socket(zmq.XREP)
        workers.bind(worker_address)

        logger.info("Binding clients' socket to %s" % self.reqrep_address)
        clients = context.socket(zmq.XREP)
        clients.bind(self.reqrep_address)

        logger.info('Starting threads')
        self.threads = []
        for i in range(self.num_threads):
            thread = SimilarityThread(i, context)
            self.threads.append(thread)
            thread.start()

        logger.info('Starting LRU device')
        self.lru_device(clients, workers)

        def cleanup(*args):
            raise KeyboardInterrupt()
        for s in [signal.SIGQUIT, signal.SIGINT, signal.SIGTERM]:
            signal.signal(s, cleanup)

        # check if threads are alive
        try:
            while True:
                for x in xrange(self.num_threads):
                    if not self.threads[x].isAlive():
                        logger.error('Thread %s is not alive, restarting.' % x)
                        self.threads[x] = self.threading_class(x, context, logger)
                        self.threads[x].start()
                time.sleep(3)
        except KeyboardInterrupt:
            logger.info('Shutting down.')
            self.stop()
            logger.info('Waiting for threads to stop.')
            self.wait_till_done()

    def lru_device(self, xrep_clients, xrep_workers):
        worker_queue = Queue.Queue()

        poller = zmq.Poller()
        poller.register(xrep_clients, zmq.POLLIN)
        poller.register(xrep_workers, zmq.POLLIN)

        logger.info('Starting LRU loop')
        while True:
            socks = dict(poller.poll())

            # handle worker activity on the backend
            if socks.has_key(xrep_workers) \
               and socks[xrep_workers] == zmq.POLLIN:
                msg = xrep_workers.recv_multipart()
                # add the worker address to the queue
                worker_queue.put(msg[0])
                # is the worker delivering or registering
                if msg[2] != 'READY':
                    # delivering, so forward to the original client
                    xrep_clients.send_multipart(msg[2:])
                continue

            # handle client activity on the frontend
            if not worker_queue.empty() \
               and socks.has_key(xrep_clients) \
               and socks[xrep_clients] == zmq.POLLIN:
                worker_addr = worker_queue.get()
                msg_in = xrep_clients.recv_multipart()
                msg_out = [worker_addr, '']+msg_in
                xrep_workers.send_multipart(msg_out)


if __name__ == '__main__':
    print '?', logger
    service = SimilarityService()
    logger.info('Starting service.')
    service.start()
    logger.info('Service stopped.')

