from twisted.web import server, resource
from twisted.internet import reactor
# from gaia_wrapper import GaiaWrapper
# from similarity_settings import LISTEN_PORT, LOGFILE, DEFAULT_PRESET, DEFAULT_NUMBER_OF_RESULTS, INDEX_NAME, PRESETS, \
#     BAD_REQUEST_CODE, NOT_FOUND_CODE, SERVER_ERROR_CODE, LOGSERVER_IP_ADDRESS, LOGSERVER_PORT, LOG_TO_STDOUT, \
#     LOG_TO_GRAYLOG
import logging
import graypy
from logging.handlers import RotatingFileHandler
# from similarity_server_utils import parse_filter, parse_target, parse_metric_descriptors
import json
import yaml
import cloghandler
import clustering_methods
import numpy as np
from gaia2 import DataSet, View, DistanceFunctionFactory

LISTEN_PORT = 8009


def server_interface(resource):
    return {
        'cluster_search_results': resource.cluster_search_results, # query, sound_ids
        'k_nearest_neighbors': resource.k_nearest_neighbors, # sound_id, k
}


class ClusteringServer(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        self.methods = server_interface(self)
        self.isLeaf = False
        self.cluster = clustering_methods.knnWeightedGraph # similarity_matrix, k
        self.request = None

    def error(self, message):
        return json.dumps({'Error': message})
    
    def getChild(self, name, request):
        return self

    def render_GET(self, request):
        return self.methods[request.prepath[1]](request=request, **request.args)

    def cluster_search_results(self, request, query, sound_ids):
        sound_ids_list = sound_ids[0].split(',')
        print('Request clustering of points: {} ... from the query "{}"'.format(', '.join(sound_ids_list[:20]), 
                                                                                query[0]))
        similarity_matrix = np.array([[1 ,0.5, 0.4, 0.01], 
                                      [0.5, 1, 0.01, 0.01], 
                                      [0.3, 0.5, 1, 0.05], 
                                      [0.01, 0.01, 0.05, 1]])
        print(similarity_matrix.shape)
        result = self.cluster(similarity_matrix, np.int(np.log2(similarity_matrix.shape[0])))
        return json.dumps(result)

    def k_nearest_neighbors(self, request, sound_id, k):
        print('Request k nearest neighbors of point {}'.format(sound_id[0]))
        ds = DataSet()
        ds.load('FS_6k_sounds_normalized.db')
        view = View(ds)
        euclideanMetric = DistanceFunctionFactory.create('euclidean', ds.layout())
        results = view.nnSearch(sound_id[0], euclideanMetric).get(int(k[0]))
        return json.dumps(results)


if __name__ == '__main__':
    # Start service
    print('Configuring clustering service...')
    root = resource.Resource()
    root.putChild("clustering", ClusteringServer())
    site = server.Site(root)
    reactor.listenTCP(LISTEN_PORT, site)
    print('Started clustering service, listening to port ' + str(LISTEN_PORT) + "...")
    reactor.run()
print('Service stopped.')
