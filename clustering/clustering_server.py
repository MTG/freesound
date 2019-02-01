from twisted.web import server, resource
from twisted.internet import reactor
from gaia_wrapper import GaiaWrapper
import numpy as np
from clustering_settings import LISTEN_PORT
import logging
import json
import networkx as nx
from networkx.readwrite import json_graph
import community as com


def server_interface(resource):
    return {
        'cluster_points': resource.cluster_points, # query, sound_ids
        'k_nearest_neighbors': resource.k_nearest_neighbors, # sound_id, k
}


class ClusteringServer(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        self.methods = server_interface(self)
        self.isLeaf = False
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

    def cluster_points(self, request, query_params, sound_ids):
        sound_ids_list = sound_ids[0].split(',')
        logger.info('Request clustering of {} points: {} ... from the query "{}"'
                .format(len(sound_ids_list), ', '.join(sound_ids_list[:20]), json.dumps(query_params)))

        # Create knn graph        
        graph = nx.Graph()
        graph.add_nodes_from(sound_ids_list)
        k = int(np.ceil(np.log2(len(sound_ids_list))))

        for sound_id in sound_ids_list:
            try:
                nearest_neighbors = self.gaia.search_nearest_neighbors(sound_id, k, sound_ids_list)
                # graph.add_edges_from([(sound_id, i[0]) for i in nearest_neighbors if i[1]<10])
                graph.add_weighted_edges_from([(sound_id, i[0], 1/i[1]) for i in nearest_neighbors if i[1]<10])
            except ValueError:  # node does not exist in Gaia dataset
                graph.remove_node(sound_id)

        # Community detection in the graph
        classes = com.best_partition(graph)

        nx.set_node_attributes(graph, classes, 'group')

        # Export graph as json
        graph_json = json_graph.node_link_data(graph)

        return json.dumps({'error': False, 'result': classes, 'graph': graph_json})

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
