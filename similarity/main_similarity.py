import time, os, subprocess, signal, uuid, traceback, zmq, Queue, logging
from settings import REQREP_ADDRESS, NUM_THREADS, LOGFILE
from threads import SimilarityThread
#from gaia_indexer import GaiaIndexer
from logging.handlers import RotatingFileHandler

logger = logging.getLogger('similarity')


class InterruptedException(Exception):
    pass

class SimilarityService():

    def __init__(self):
        logger.info('Initializing similarity service')
        self.num_threads = NUM_THREADS
        self.reqrep_address = REQREP_ADDRESS
        self.__stop = False

    def stop(self):
        logger.info('Stopping service.')
        self.__stop = True

    def stop_threads(self):
        logger.info('Stopping threads.')
        for x in xrange(self.num_threads):
            self.threads[x].stop()

    def wait_till_done(self):
        logger.info('Waiting till threads are done.')
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

        def cleanup(*args):
            logger.warning('Caught interrupt!')
            self.stop()

        for s in [signal.SIGQUIT,
                  signal.SIGINT,
                  signal.SIGTERM,
                  signal.SIGABRT,
                  signal.SIGHUP]:
            signal.signal(s, cleanup)


        logger.info('Starting LRU device')
        self.lru_device(clients, workers)
        self.stop_threads()
        self.wait_till_done()
        logger.info('Shutting down.')
        logger.info('Waiting for threads to stop.')

    def lru_device(self, xrep_clients, xrep_workers):
        worker_queue = Queue.Queue()

        poller = zmq.Poller()
        poller.register(xrep_clients, zmq.POLLIN)
        poller.register(xrep_workers, zmq.POLLIN)

        logger.info('Starting LRU loop')
        while not self.__stop:
            print 'outer loop'

            try:
                while not self.__stop:
                    print 'polling'
                    socks = dict(poller.poll(1000))
                    if len(socks.keys()) > 0:
                        break
                    else:
                        continue
            except zmq.ZMQError:
                self.stop()

            if self.__stop:
                break

            # handle worker activity on the backend
            if socks.has_key(xrep_workers) and socks[xrep_workers] == zmq.POLLIN:
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
    # set up logging
    logger      = logging.getLogger('similarity')
    logger.setLevel(logging.DEBUG)
    handler     = RotatingFileHandler(LOGFILE,
                                      maxBytes=2*1024*1024,
                                      backupCount=5)
    handler.setLevel(logging.DEBUG)
    std_handler = logging.StreamHandler()
    std_handler.setLevel(logging.DEBUG)
    formatter   = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    std_handler.setFormatter(formatter)
    logger.addHandler(std_handler)

    service = SimilarityService()
    logger.info('Starting service.')
    service.start()
    logger.info('Service stopped.')

