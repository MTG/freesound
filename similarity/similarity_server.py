from twisted.web import server, resource
from twisted.internet import reactor
from gaia_wrapper import GaiaWrapper
from similarity_settings import LISTEN_PORT, LOGFILE, DEFAULT_PRESET, DEFAULT_NUMBER_OF_RESULTS, INDEX_NAME, PRESETS
import logging
import graypy
from logging.handlers import RotatingFileHandler
from similarity_server_utils import parse_filter, parse_target
import json

def server_interface(resource):
    return {
        'add_point':resource.add_point, # location, sound_id
        'delete_point':resource.delete_point, # sound_id
        'contains':resource.contains, # sound_id
        'nnsearch':resource.nnsearch, # sound_id, num_results (optional), preset (optional)
        'nnrange':resource.nnrange,  # target, filter, num_results (optional)
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
        return json.dumps( self.gaia.add_point(location[0],sound_id[0]))

    def delete_point(self, sound_id):
        return json.dumps(self.gaia.delete_point(sound_id[0]))

    def contains(self, sound_id):
        return json.dumps(self.gaia.contains(sound_id[0]))

    def nnsearch(self,sound_id,num_results = None,preset = None):
        if not preset:
            preset = [DEFAULT_PRESET]
        else:
            if preset[0] not in PRESETS:
                preset = [DEFAULT_PRESET]
        if not num_results:
            num_results = [DEFAULT_NUMBER_OF_RESULTS]

        return json.dumps(self.gaia.search_dataset(sound_id[0], num_results[0], preset_name = preset[0]))

    def nnrange(self, target = None, filter = None, num_results = None):
        if not filter and not target:
            return json.dumps({'error':True,'result':"At least introduce either a filter or a target"})

        if not num_results:
            num_results = [DEFAULT_NUMBER_OF_RESULTS]

        if filter:
            filter = filter[0]
            pf = parse_filter(filter.replace("'",'"'))
        else:
            pf = []

        if target:
            target = target[0]
            pt = parse_target(target.replace("'",'"'))
        else:
            pt = {}

        if type(pf) != list or type(pt) != dict:
            message = ""
            if type(pf) == str:
                message += pf
            if type(pt) == str:
                message += pt
            if message == "":
                message = "Invalid filter or target."

            return json.dumps({'error':True,'result':message})
            #raise ReturnError(400, "BadRequest", {"explanation": message})

        return json.dumps(self.gaia.query_dataset({'target':pt,'filter':pf}, num_results[0]))

    def save(self, filename = None):
        if not filename:
            filename = [INDEX_NAME]

        return json.dumps(self.gaia.save_index(filename[0]))


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
    handler_graypy = graypy.GELFHandler('10.55.0.48', 12201)
    logger.addHandler(handler_graypy)

    # Start service
    logger.info('Configuring similarity service...')
    root = resource.Resource()
    root.putChild("similarity",SimilarityServer())
    site = server.Site(root)
    reactor.listenTCP(LISTEN_PORT, site)
    logger.info('Started similarity service, listening to port ' + str(LISTEN_PORT) + "...")
    reactor.run()
    logger.info('Service stopped.')


