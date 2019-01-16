from twisted.web import server, resource
from twisted.internet import reactor
from gaia_wrapper import GaiaWrapper
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
import networkx as nx
import community.community_louvain as com

LISTEN_PORT = 8009
LOGFILE = '/var/log/freesound/clustering.log'
LOG_TO_STDOUT = True


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
        self.gaia = GaiaWrapper()
        self.request = None

    def error(self, message):
        return json.dumps({'Error': message})
    
    def getChild(self, name, request):
        return self

    def render_GET(self, request):
        return self.methods[request.prepath[1]](request=request, **request.args)

    def render_POST(self, request):
        return self.methods[request.prepath[1]](request=request, **request.args)

    def cluster_search_results(self, request, query, sound_ids):
        sound_ids_list = sound_ids[0].split(',')
        logger.info('Request clustering of {} points: {} ... from the query "{}"'
                .format(len(sound_ids_list), ', '.join(sound_ids_list[:20]), query[0]))

        # Create knn graph        
        graph = nx.Graph()
        graph.add_nodes_from(sound_ids_list)

        for sound_id in sound_ids_list:
            nearest_neighbors, _ = zip(*self.gaia.search_nearest_neighbors(sound_id, 10, sound_ids_list))
            graph.add_edges_from([(sound_id, i) for i in nearest_neighbors])

        # Community detection in the graph
        classes = com.best_partition(graph)
        return json.dumps(classes)

    def k_nearest_neighbors(self, request, sound_id, k):
        logger.info('Request k nearest neighbors of point {}'.format(sound_id[0]))
        results = self.gaia.search_nearest_neighbors(sound_id[0], int(k[0]))
        return json.dumps(results)


if __name__ == '__main__':
    # Set up logging
    logger = logging.getLogger('clustering')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Start service
    logger.info('Configuring clustering service...')
    root = resource.Resource()
    root.putChild("clustering", ClusteringServer())
    site = server.Site(root)
    reactor.listenTCP(LISTEN_PORT, site)
    logger.info('Started clustering service, listening to port ' + str(LISTEN_PORT) + "...")
    reactor.run()
    logger.info('Service stopped.')
