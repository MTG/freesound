import os, sys
from time import time
import logging
from django.conf import settings

# The following packages are only needed if the running process is configured to be a Celery worker. 
# We avoid importing them in appservers to avoid having to install unneeded dependencies.
if settings.ENV_CELERY_WORKER == '1':
    from gaia_wrapper import GaiaWrapper
    import numpy as np
    from sklearn import metrics
    from sklearn.feature_selection import mutual_info_classif
    from clustering_settings import clustering_settings as clust_settings
    import json
    import networkx as nx
    from networkx.readwrite import json_graph
    import community as com
    from networkx.algorithms.community import k_clique_communities, greedy_modularity_communities

logger = logging.getLogger('clustering')


class ClusteringEngine():
    def __init__(self):
        self.gaia = GaiaWrapper()

    def _prepare_clustering_result_for_evaluation(self, classes):
        sound_ids_list, clusters = zip(*classes.items())
        tag_features = self.gaia.return_sound_tag_features(sound_ids_list)
        idx_to_remove = set([idx for idx, feature in enumerate(tag_features) if feature == None])  # sound not in gaia tag dataset
        tag_features_filtered = [f for idx, f in enumerate(tag_features) if idx not in idx_to_remove]
        clusters_filtered = [c for idx, c in enumerate(clusters) if idx not in idx_to_remove]
        return tag_features_filtered, clusters_filtered

    def _average_mutual_information_tags_clusters(self, classes):
        tag_features, clusters = self._prepare_clustering_result_for_evaluation(classes)
        return np.average(mutual_info_classif(tag_features, clusters, discrete_features=True))

    def _silouhette_coeff_tags_clusters(self, classes):
        tag_features, clusters = self._prepare_clustering_result_for_evaluation(classes)
        return metrics.silhouette_score(tag_features, clusters, metric='euclidean')

    def _calinski_idx_tags_clusters(self, classes):
        tag_features, clusters = self._prepare_clustering_result_for_evaluation(classes)
        return metrics.calinski_harabaz_score(tag_features, clusters)
    
    def _davies_idx_tags_clusters(self, classes):
        # not included in current used sklearn version
        tag_features, clusters = self._prepare_clustering_result_for_evaluation(classes)
        return metrics.davies_bouldin_score(tag_features, clusters)

    def _evaluation_metrics(self, classes):
        tag_features, clusters = self._prepare_clustering_result_for_evaluation(classes)
        ami = np.average(mutual_info_classif(tag_features, clusters, discrete_features=True))  # set to False if lda is used
        ss = metrics.silhouette_score(tag_features, clusters, metric='euclidean')
        ci = metrics.calinski_harabaz_score(tag_features, clusters)
        return ami, ss, ci

    def _ratio_intra_community_edges(self, graph, communities):
        # Assess individual communities quality
        community_num_nodes = [len(community) for community in communities]
        # counts the number of edges inside a community
        intra_community_edges = [graph.subgraph(block).size() for block in communities]
        # counts the number of edges from nodes in a community to nodes inside or outside the same community
        total_community_edges = [sum([graph.degree(node_id) for node_id in community])-intra_community_edges[i] 
                                                            for i, community in enumerate(communities)]
        # ratio (high value -> good cluster)
        ratio_intra_community_edges = [round(a/float(b), 2) for a,b in zip(intra_community_edges, total_community_edges)]

        return ratio_intra_community_edges

    def _point_centralities(self, graph, communities):
        # Find representative examples of cluster, partitions central nodes
        subgraphs = [graph.subgraph(community) for community in communities]
        communities_centralities = [nx.algorithms.centrality.degree_centrality(subgraph) for subgraph in subgraphs]

        # merge and normalize in each community
        node_community_centralities = {k: v/max(d.values()) for d in communities_centralities for k, v in d.items()}

        return node_community_centralities
    
    def _save_results_to_file(self, query_params, features, graph_json, sound_ids, modularity, 
                              num_communities, ratio_intra_community_edges, ami, ss, ci, communities):
        if clust_settings.get('SAVE_RESULTS_FOLDER', None):
            result = {
                'query_params' : query_params,
                'sound_ids': sound_ids,
                'num_clusters': num_communities,
                'graph': graph_json,
                'features': features,
                'modularity': modularity,
                'ratio_intra_community_edges': ratio_intra_community_edges,
                'average_mutual_information_tags': ami,
                'silouhette_coeff_tags': ss,
                'calinski_harabaz_score': ci,
                'communities': communities
            }
            json.dump(result, open('{}/{}.json'.format(clust_settings.get('SAVE_RESULTS_FOLDER'), query_params[0]), 'w'))

    def create_knn_graph(self, sound_ids_list, features='audio_as'):
        # Create k nearest neighbors graph        
        graph = nx.Graph()
        graph.add_nodes_from(sound_ids_list)
        k = int(np.ceil(np.log2(len(sound_ids_list))))
        k = 5

        for sound_id in sound_ids_list:
            try:
                nearest_neighbors = self.gaia.search_nearest_neighbors(sound_id, k, sound_ids_list, features=features)
                # edges += [(sound_id, i[0]) for i in nearest_neighbors if i[1]<20]
                graph.add_edges_from([(sound_id, i[0]) for i in nearest_neighbors if i[1]<20])
                # graph.add_weighted_edges_from([(sound_id, i[0], 1/i[1]) for i in nearest_neighbors if i[1]<10])
            except ValueError:  # node does not exist in Gaia dataset
                graph.remove_node(sound_id)

        # Remove isolated nodes
        graph.remove_nodes_from(list(nx.isolates(graph)))

        return graph

    def create_common_nn_graph(self, sound_ids_list, features='audio_as'):
        # first create a knn graph
        knn_graph = self.create_knn_graph(sound_ids_list, features=features)

        # create the common nn graph
        graph = nx.Graph()
        graph.add_nodes_from(knn_graph.nodes)

        for i, node_i in enumerate(knn_graph.nodes):
            for j, node_j in enumerate(knn_graph.nodes):
                if j > i:
                    num_common_neighbors = len(set(knn_graph.neighbors(node_i)).intersection(knn_graph.neighbors(node_j)))
                    if num_common_neighbors > 0:
                        graph.add_edge(node_i, node_j, weight=num_common_neighbors)

        # keep only k most weighted edges
        k = int(np.ceil(np.log2(len(graph.nodes))))
        for node in graph.nodes:
            ordered_neighbors = sorted(list(graph[node].iteritems()), key=lambda x: x[1]['weight'], reverse=True)
            try:
                neighbors_to_remove = zip(*ordered_neighbors[k:])[0]
                graph.remove_edges_from(zip([node]*len(neighbors_to_remove), neighbors_to_remove))
            except IndexError:
                pass

        # Remove isolated nodes
        graph.remove_nodes_from(list(nx.isolates(graph)))

        return graph

    def cluster_graph(self, graph):
        # Community detection in the graph
        classes = com.best_partition(graph)
        num_communities = max(classes.values()) + 1
        communities = [[key for key, value in classes.iteritems() if value==i] for i in range(num_communities)]

        # overall quality (modularity of the partition)
        modularity = com.modularity(classes, graph)

        return classes, num_communities, communities, modularity

    def cluster_graph_overlap(sefl, graph, k=5):
        communities = [list(community) for community in k_clique_communities(graph, k)]
        # communities = [list(community) for community in greedy_modularity_communities(graph)]
        greedy_modularity_communities
        num_communities = len(communities)
        classes = {sound_id: cluster_id for cluster_id, cluster in enumerate(communities) for sound_id in cluster}

        return  classes, num_communities, communities, None

    def remove_lowest_quality_cluster(self, graph, classes, communities, ratio_intra_community_edges):
        if len(communities) < 3:  # if two clusters or less, we do not remove any
            return graph, classes, communities, ratio_intra_community_edges
        min_ratio_idx = np.argmin(ratio_intra_community_edges)
        sounds_to_remove = communities[min_ratio_idx]
        graph.remove_nodes_from(sounds_to_remove)
        del communities[min_ratio_idx]
        for snd in sounds_to_remove:
            del classes[snd]
        del ratio_intra_community_edges[min_ratio_idx]
        for idx in range(min_ratio_idx, max(classes.values())):
            for snd in communities[idx]:
                classes[snd] -= 1
        return graph, classes, communities, ratio_intra_community_edges

    def cluster_points(self, query_params, features, sound_ids):
        start_time = time()
        sound_ids_list = [str(fs_id) for fs_id in sound_ids.split(',')]
        logger.info('Request clustering of {} points: {} ... from the query "{}"'
                .format(len(sound_ids_list), ', '.join(sound_ids_list[:20]), json.dumps(query_params)))

        graph = self.create_knn_graph(sound_ids_list, features=features)
        # graph = self.create_common_nn_graph(sound_ids_list, features=features)

        if len(graph.nodes) == 0:  # the graph does not contain any node
            return {'error': False, 'result': None, 'graph': None}

        classes, num_communities, communities, modularity = self.cluster_graph(graph)
        # classes, num_communities, communities, modularity = self.cluster_graph_overlap(graph)
        ratio_intra_community_edges = self._ratio_intra_community_edges(graph, communities)

        # graph, classes, communities, ratio_intra_community_edges = self.remove_lowest_quality_cluster(
        #         graph, classes, communities, ratio_intra_community_edges)

        node_community_centralities = self._point_centralities(graph, communities)

        # Add cluster and centralities info to graph
        nx.set_node_attributes(graph, classes, 'group')
        nx.set_node_attributes(graph, node_community_centralities, 'group_centrality')

        # Evaluation metrics vs tag features
        ami, ss, ci = self._evaluation_metrics(classes)

        end_time = time()
        logger.info('Clustering done! It took {} seconds. '
                    'Modularity: {}, '
                    'Average ratio_intra_community_edges: {}, '
                    'Average Mutual Information with tags: {}, '
                    'Silouhette Coefficient with tags: {}, '
                    'Calinski Index with tags: {}, '
                    'Davies Index with tags: {}'
                    .format(end_time-start_time, modularity, np.mean(ratio_intra_community_edges), ami, ss, ci, None))

        # Export graph as json
        graph_json = json_graph.node_link_data(graph)

        # self._save_results_to_file(query_params, features, graph_json, sound_ids, modularity, 
        #                            num_communities, ratio_intra_community_edges, ami, ss, ci, communities)

        return {'error': False, 'result': communities, 'graph': graph_json}

    def k_nearest_neighbors(self, sound_id, k):
        logger.info('Request k nearest neighbors of point {}'.format(sound_id[0]))
        results = self.gaia.search_nearest_neighbors(sound_id[0], int(k[0]))
        return json.dumps(results)
