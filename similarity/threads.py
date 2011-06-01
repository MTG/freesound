import threading, zmq, traceback, time, os, json
from global_indexer import indexer
from logger import logger


class SimilarityThread(threading.Thread):

    def __init__(self, id, ctx):
        logger.debug('Starting thread %s' % id)
        threading.Thread.__init__(self)
        self.id = id
        # set up zmq queue connection
        self.ctx = ctx
        self.__stop = False
        self.return_address = []


    def empty_reply(self):
        self.__reply('')


    def reply(self, msg):
        self.__reply(json.dumps(msg))


    def reply_exception(self, exception):
        self.reply({'exception': True, 'info': str(exception)})


    def __reply(self, msg):
        self.socket.send_multipart(self.return_address+[msg])
        self.REPLIED = True


    def stop(self):
        self.__stop = True


    def handle_message(self, msg):
        if not indexer:
            raise Exception('The Gaia Indexer is starting up, please try again later.')

        elif msg['type'] == 'Search':
            sound_id = msg.get('sound_id', False)
            preset = msg.get('preset', False)
            results = msg.get('num_results', 10)
            if not sound_id or not preset:
                raise Exception("You should specify at least a sound_id and a preset.")
            res = indexer.search(str(sound_id), results, str(preset))
            self.reply(res)

        elif msg['type'] == 'AddSound':
            sound_id = msg.get('sound_id', False)
            yaml  = msg.get('yaml', False)
            if not sound_id or not yaml:
                raise Exception('The sound_id and yaml parameters should both be present.')
            if not os.path.exists(yaml):
                raise Exception('The yaml path specified appears to not exist (%s).' % yaml)
            indexer.add(str(yaml), str(sound_id))
            self.empty_reply()

        elif msg['type'] == 'DeleteSound':
            sound_id = msg.get('sound_id', False)
            if not sound_id:
                raise Exception('The sound_id should be specified.')
            indexer.delete(str(sound_id))
            self.empty_reply()

        return


    def run(self):
        while True:
            try:
                self.socket = self.ctx.socket(zmq.REQ)
                self.socket.connect('inproc://workers')
                self.socket.send('READY')

                self.poller = zmq.Poller()
                self.poller.register(self.socket, zmq.POLLIN)

                while not self.__stop:
                    self.REPLIED = False

                    while True:
                        socks = dict(self.poller.poll(1000))
                        if len(socks.keys()) > 0:
                            break
                        else:
                            continue

                    assert(socks[self.socket] == zmq.POLLIN)

                    msg_received = self.socket.recv_multipart()
                    self.return_address = msg_received[:-1]
                    msg_received = msg_received[-1]

                    try:
                        msg = json.loads(msg_received)
                        self.handle_message(msg)
                        if not self.REPLIED:
                            warning = 'Thread %s: Nothing was replied, the message was not handled.' % self.id
                            logger.warn(warning)
                            raise Exception("This message wasn't understood: \n\t%s" % msg_received)
                    except Exception, e:
                        logger.error('Thread %s: caught Exception: %s\n%s' % (self.id, str(e), traceback.format_exc()))
                        self.reply_exception(e)

            except AssertionError, e:
                logger.error('Could not assert right socket state, creating new socket.')
            except zmq.ZMQError, e:
                logger.error('Could not send or receive message, creating new socket.')
            finally:
                self.poller.unregister(self.socket)
                self.socket.close()
