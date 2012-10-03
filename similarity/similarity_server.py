from twisted.web import server, resource
from twisted.internet import reactor
from gaia_wrapper import GaiaWrapper
from similarity_settings import LISTEN_PORT, LOGFILE, DEFAULT_PRESET, DEFAULT_NUMBER_OF_RESULTS, INDEX_NAME
import logging
from logging.handlers import RotatingFileHandler
import json

def server_interface(resource):
    return {
        'add_point':resource.add_point, # location, sound_id
        'delete_point':resource.delete_point, # sound_id
        'contains':resource.contains, # sound_id
        'nnsearch':resource.nnsearch, # sound_id, num_results
        'nnrange':resource.nnrange,  # query_parameters, num_results
        'save':resource.save # filename (optional)
    }

class SimilarityServer(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        self.methods = server_interface(self)
        self.isLeaf = False
        self.gaia = GaiaWrapper()

    def error(self,message):
        return json.dumps({'Error':message})

    def getChild(self, name, request):
        return self

    def render_GET(self, request):
        return self.methods[request.prepath[1]](**request.args)

    def add_point(self,location,sound_id):
        self.gaia.add_point(location[0],sound_id[0])
        return json.dumps({'result':'OK'})

    def delete_point(self, sound_id):
        self.gaia.delete_point(sound_id[0])
        return json.dumps({'result':'OK'})

    def contains(self, sound_id):
        return json.dumps({'result':self.gaia.contains(sound_id[0])})

    def nnsearch(self,sound_id,num_results = None,preset = None):
        if not preset:
            preset = [DEFAULT_PRESET]
        if not num_results:
            num_results = [DEFAULT_NUMBER_OF_RESULTS]

        result = self.gaia.search_dataset(sound_id[0], num_results[0], preset_name = preset[0])
        return json.dumps({'result':result})

    def nnrange(self, query_parameters, num_results):
        result = self.gaia.query_dataset(json.loads(query_parameters[0]), num_results[0])

    def save(self, filename = None):
        if not filename:
            filename = [INDEX_NAME]

        self.gaia.save_index(filename[0])
        return json.dumps({'result':'OK'})


if __name__ == '__main__':
    # Set up logging
    logger = logging.getLogger('similarity')
    logger.setLevel(logging.DEBUG)
    handler = RotatingFileHandler(LOGFILE, maxBytes=2*1024*1024, backupCount=5)
    handler.setLevel(logging.DEBUG)
    std_handler = logging.StreamHandler()
    std_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    std_handler.setFormatter(formatter)
    logger.addHandler(std_handler)

    # Start service
    logger.info('Configuring similarity service...')
    root = resource.Resource()
    root.putChild("similarity",SimilarityServer())
    site = server.Site(root)
    reactor.listenTCP(LISTEN_PORT, site)
    logger.info('Started similarity service, listening to port ' + str(LISTEN_PORT) + "...")
    reactor.run()
    logger.info('Service stopped.')


