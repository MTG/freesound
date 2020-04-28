import os, sys
from time import time
import logging
from django.conf import settings

import clustering_settings as clust_settings

# The following packages are only needed if the running process is configured to be a Celery worker. 
# We avoid importing them in appservers to avoid having to install unneeded dependencies.
if settings.IS_CELERY_WORKER:
    from gaia_wrapper import GaiaWrapperClustering
    import numpy as np
    from sklearn import metrics
    from sklearn.feature_selection import mutual_info_classif
    import json
    import networkx as nx
    from networkx.readwrite import json_graph
    import community as com
    from networkx.algorithms.community import k_clique_communities, greedy_modularity_communities
    import faiss

logger = logging.getLogger('clustering')


class ClusteringEngine():
    """Clustering Engine class.

    This class regroups various methods for performing clustering on a set of sounds.

    Instead of directly using the audio feature space for performing the clustering, it creates a 
    K-Nearest Neighbors Graph that is then partitioned for obtaining the clusters.
    It relies on Gaia for performing nearest neighbor searches on a multi-dimentional feature space
    (in gaia_wrapper.py file). The available features used for clustering are listed in the 
    clustering_settings.py file. It requires building the Gaia dataset index file in advanced.

    It also includes some methods that enable to automaticaly estimate the performance of the clustering
    method. Moreover, a few unsued alternative methods for performing some intermediate steps are left 
    here for developement and research purpose.
    """
    def __init__(self):
        self.gaia = GaiaWrapperClustering()

    def _prepare_clustering_result_and_reference_features_for_evaluation(self, classes):
        """Formats the clustering classes and some reference features in order to then estimate how good is the 
        clustering performance. Tipically the reference features can be tag-derived features that reflect semantic 
        characteristics of the content. The reference features are defined in the clustering settings file.
        
        Extracts reference features for the sounds given as keys of the classes argument.
        Prepares classes and extracted features in lists in order to compare them.
        Removes sounds with missing features.

        Args:
            classes (Dict{Int: Int}): clustering classes for each sound {<sound_id>: <class_idx>}.

        Returns:
            Tuple(List[List[Float]], List[Int]): 2-element tuple containing a list of evaluation features 
                and list of classes (clusters) idx.
        """
        sound_ids_list, clusters = zip(*classes.items())
        reference_features = self.gaia.return_sound_reference_features(sound_ids_list)

        # Remove sounds that are not in the gaia reference dataset
        idx_to_remove = set([idx for idx, feature in enumerate(reference_features) if feature == None])
        reference_features_filtered = [f for idx, f in enumerate(reference_features) if idx not in idx_to_remove]
        clusters_filtered = [c for idx, c in enumerate(clusters) if idx not in idx_to_remove]

        return reference_features_filtered, clusters_filtered

    def _average_mutual_information_reference_features_clusters(self, classes):
        """Estimates Average Mutual Information between reference features and the given clustering classes.

        Args:
            classes (Dict{Int: Int}): clustering classes for each sound {<sound_id>: <class_idx>}.

        Returns:
            Numpy.float: Average Mutual Information.
        """
        reference_features, clusters = self._prepare_clustering_result_and_reference_features_for_evaluation(classes)
        return np.average(mutual_info_classif(reference_features, clusters, discrete_features=True))

    def _silouhette_coeff_reference_features_clusters(self, classes):
        """Computes mean Silhouette Coefficient score between reference features and the given clustering classes.

        Args:
            classes (Dict{Int: Int}): clustering classes for each sound {<sound_id>: <class_idx>}.

        Returns:
            Numpy.float: mean Silhouette Coefficient.
        """
        reference_features, clusters = self._prepare_clustering_result_and_reference_features_for_evaluation(classes)
        return metrics.silhouette_score(reference_features, clusters, metric='euclidean')

    def _calinski_idx_reference_features_clusters(self, classes):
        """Computes the Calinski and Harabaz score between reference features and the given clustering classes.

        Args:
            classes (Dict{Int: Int}): clustering classes for each sound {<sound_id>: <class_idx>}.

        Returns:
            Numpy.float: Calinski and Harabaz score.
        """
        reference_features, clusters = self._prepare_clustering_result_and_reference_features_for_evaluation(classes)
        return metrics.calinski_harabaz_score(reference_features, clusters)
    
    def _davies_idx_reference_features_clusters(self, classes):
        """Computes the Davies-Bouldin score between reference features and the given clustering classes.

        Args:
            classes (Dict{Int: Int}): clustering classes for each sound {<sound_id>: <class_idx>}.

        Returns:
            Numpy.float: Davies-Bouldin score.
        """
        # This metric is not included in current used sklearn version
        reference_features, clusters = self._prepare_clustering_result_and_reference_features_for_evaluation(classes)
        return metrics.davies_bouldin_score(reference_features, clusters)

    def _evaluation_metrics(self, classes):
        """Computes different scores related to the clustering performance by comparing the resulting clustering classes
        to the reference features defined in the clustering settings file. The reference features tipically correspond to 
        tag-derived features that can reflect semantic characteristics of the audio clips.

        Args:
            classes (Dict{Int: Int}): clustering classes for each sound {<sound_id>: <class_idx>}.

        Returns:
            Tuple(Numpy.float, Numpy.float, Numpy.float): 3-element tuple containing the Average Mutual Information
                score, the Silhouette Coefficient and the Calinski and Harabaz score.
        """
        # we compute the evaluation metrics only if some reference features are available for evaluation
        # we return None when they are not available not to break the following part of the code
        if clust_settings.REFERENCE_FEATURES in clust_settings.AVAILABLE_FEATURES:
            reference_features, clusters = self._prepare_clustering_result_and_reference_features_for_evaluation(classes)
            ami = np.average(mutual_info_classif(reference_features, clusters, discrete_features=True))
            ss = metrics.silhouette_score(reference_features, clusters, metric='euclidean')
            ci = metrics.calinski_harabaz_score(reference_features, clusters)
            return ami, ss, ci
        else:
            return None, None, None

    def _ratio_intra_community_edges(self, graph, communities):
        """Computes the ratio of the number of intra-community (cluster) edges to the total number of edges in the cluster.

        This may be useful for estimating how distinctive each cluster is against the other clusters.

        Args:
            graph (nx.Graph): NetworkX graph representation of sounds.
            communities (List[List[Int]]): List storing Lists containing the Sound ids that are in each community (cluster).

        Returns:
            List[Float]: ratio value for each cluster.
        """
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
        """Computes graph centrality of each node in the given communities (clusters) of the given graph.

        This may be useful for selecting representative examples of a cluster. A sound that is central in his cluster may be
        represent what a cluster contains the most.

        Args:
            graph (nx.Graph): NetworkX graph representation of sounds.
            communities (List[List[Int]]): List storing Lists containing the Sound ids that are in each community (cluster).

        Returns:
            Dict{Int: Float}: Dict containing the community centrality value for each sound 
                ({<sound_id>: <community_centrality>}).
        """
        # 
        subgraphs = [graph.subgraph(community) for community in communities]
        communities_centralities = [nx.algorithms.centrality.degree_centrality(subgraph) for subgraph in subgraphs]

        # merge and normalize in each community
        node_community_centralities = {k: v/max(d.values()) for d in communities_centralities for k, v in d.items()}

        return node_community_centralities
    
    def _save_results_to_file(self, query_params, features, graph_json, sound_ids, modularity, 
                              num_communities, ratio_intra_community_edges, ami, ss, ci, communities):
        """Saves a json file to disk containing the clustering results information listed below.

        This is used when developing the clustering method. The results and the evaluation metrics are made accessible 
        for post-analysis.
        
        Args:
            query_params (str): string representing the query parameters submited by the user to the search engine.
            features (str): name of the features used for clustering. 
            graph_json: (dict) NetworkX graph representation of sounds data in node-link format that is suitable for JSON 
                serialization.
            sound_ids (List[Int]): list of the sound ids.
            modularity (float): modularity of the graph partition.
            num_communities (Int): number of communities (clusters).
            ratio_intra_community_edges (List[Float]): intra-community edges ratio.
            ami (Numpy.float): Average Mutual Information score.
            ss (Numpy.float): Silhouette Coefficient score.
            ci (Numpy.float): Calinski and Harabaz Index score.
            communities (List[List[Int]]): List storing Lists containing the Sound ids that are in each community (cluster).
        """
        if clust_settings.SAVE_RESULTS_FOLDER:
            result = {
                'query_params' : query_params,
                'sound_ids': sound_ids,
                'num_clusters': num_communities,
                'graph': graph_json,
                'features': features,
                'modularity': modularity,
                'ratio_intra_community_edges': ratio_intra_community_edges,
                'average_mutual_information': ami,
                'silouhette_coeff': ss,
                'calinski_harabaz_score': ci,
                'communities': communities
            }
            json.dump(result, open('{}/{}.json'.format(clust_settings.SAVE_RESULTS_FOLDER, query_params[0]), 'w'))

    def create_knn_graph(self, sound_ids_list, features=clust_settings.DEFAULT_FEATURES):
        """Creates a K-Nearest Neighbors Graph representation of the given sounds.

        Args:
            sound_ids_list (List[str]): list of sound ids.
            features (str): name of the features to be used for nearest neighbors computation. 
                Available features are listed in the clustering settings file.

        Returns:
            (nx.Graph): NetworkX graph representation of sounds.
        """
        # Create k nearest neighbors graph        
        graph = nx.Graph()
        graph.add_nodes_from(sound_ids_list)
        # we set k to log2(N), where N is the number of elements to cluster. This allows us to reach a sufficient number of 
        # neighbors for small collections, while limiting it for larger collections, which ensures low-computational complexity.
        k = int(np.ceil(np.log2(len(sound_ids_list))))

        for sound_id in sound_ids_list:
            try:
                nearest_neighbors = self.gaia.search_nearest_neighbors(sound_id, k, sound_ids_list, features=features)
                # edges += [(sound_id, i[0]) for i in nearest_neighbors if i[1]<clust_settings.MAX_NEIGHBORS_DISTANCE]
                graph.add_edges_from([(sound_id, i[0]) for i in nearest_neighbors if i[1]<clust_settings.MAX_NEIGHBORS_DISTANCE])
                # graph.add_weighted_edges_from([(sound_id, i[0], 1/i[1]) for i in nearest_neighbors if i[1]<clust_settings.MAX_NEIGHBORS_DISTANCE])
            except ValueError:  # node does not exist in Gaia dataset
                graph.remove_node(sound_id)

        # sound_features, sound_ids_out = self.gaia.return_features(sound_ids_list)
        # # sound_features = np.array(sound_features).astype('float32')
        # # index = faiss.IndexFlatL2(sound_features.shape[-1])
        # # index.add(sound_features)
        # # D, I = index.search(sound_features, k)

        # D, I = self.search_knn(sound_features, sound_features, k+1)

        # for sound_id, nearest_neighbors, distances in zip(sound_ids_list, I, D):
        #     try:
        #         graph.add_edges_from([(sound_id, sound_ids_out[i]) for i, d in zip(nearest_neighbors[1:], distances[1:]) 
        #                               if d < clust_settings.MAX_NEIGHBORS_DISTANCE])
        #     except ValueError:  # node does not exist in Gaia dataset
        #         graph.remove_node(sound_id)

        # Remove isolated nodes
        graph.remove_nodes_from(list(nx.isolates(graph)))

        return graph

    def create_common_nn_graph(self, sound_ids_list, features=clust_settings.DEFAULT_FEATURES):
        """Creates a Common Nearest Neighbors Graph representation of the given sounds.

        Args:
            sound_ids_list (List[str]): list of sound ids.
            features (str): name of the features to be used for nearest neighbors computation. 
                Available features are listed in the clustering settings file.

        Returns:
            (nx.Graph): NetworkX graph representation of sounds.
        """
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
        """Applies community detection in the given graph.

        Uses the Louvain method to extract communities from the given graph.

        Args:
            graph (nx.Graph): NetworkX graph representation of sounds.

        Returns:
            Tuple(Dict{Int: Int}, int, List[List[Int]], float): 4-element tuple containing the clustering classes for each sound 
                {<sound_id>: <class_idx>}, the number of communities (clusters), the sound ids in the communities and
                the modularity of the graph partition.
        
        """ 
        # Community detection in the graph
        classes = com.best_partition(graph)
        num_communities = max(classes.values()) + 1
        communities = [[key for key, value in classes.iteritems() if value==i] for i in range(num_communities)]

        # overall quality (modularity of the partition)
        modularity = com.modularity(classes, graph)

        return classes, num_communities, communities, modularity

    def cluster_graph_overlap(sefl, graph, k=5):
        """Applies overlapping community detection in the given graph.

        Uses the percolation method for finding the k-clique communities in the given graph.
        This method returns 4 elements to follow the same structure as cluster_graph().
        However the modularity of an overlapping partition cannot be defined, we return None instead.

        Args:
            graph (nx.Graph): NetworkX graph representation of sounds.

        Returns:
            Tuple(Dict{Int: Int}, int, List[List[Int]], None): 4-element tuple containing the clustering classes for each sound 
                {<sound_id>: <class_idx>}, the number of communities (clusters), the sound ids in the communities and
                None.
        """ 
        communities = [list(community) for community in k_clique_communities(graph, k)]
        # communities = [list(community) for community in greedy_modularity_communities(graph)]
        greedy_modularity_communities
        num_communities = len(communities)
        classes = {sound_id: cluster_id for cluster_id, cluster in enumerate(communities) for sound_id in cluster}

        return  classes, num_communities, communities, None

    def remove_lowest_quality_cluster(self, graph, classes, communities, ratio_intra_community_edges):
        """Removes the lowest quality cluster in the given graph.

        Discards the cluster that has the lowest ratio of the number of intra-community edges. Removes the related values 
        of the removed cluster from the given clustering information.

        Args:
            graph (nx.Graph): NetworkX graph representation of sounds.
            classes (Dict{Int: Int}): clustering classes for each sound {<sound_id>: <class_idx>}.
            communities (List[List[Int]]): List storing Lists containing the Sound ids that are in each community (cluster).
            ratio_intra_community_edges (List[Float]): intra-community edges ratio.

        Returns:
            Tuple(nx.Graph, Dict{Int: Int}, List[List[Int]], List[float]): 4-element tuple containing the graph representation 
            of the sounds, the clustering classes for each sound {<sound_id>: <class_idx>}, the sound ids in the communities 
            and the ratio of intra-community edges in each cluster.
        """
        # if two clusters or less, we do not remove any
        if len(communities) <= 2:
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
        """Applies clustering on the requested sounds using the given features name.

        Args:
            query_params (str): string representing the query parameters submited by the user to the search engine.
            features (str): name of the features used for clustering the sounds.
            sound_ids (List[int]): list containing the ids of the sound to cluster.
        
        Returns:
            Dict: contains the resulting clustering classes and the graph in node-link format suitable for JSON serialization.
        """
        start_time = time()
        sound_ids = [str(s) for s in sound_ids]
        logger.info('Request clustering of {} points: {} ... from the query "{}"'
                .format(len(sound_ids), ', '.join(sound_ids[:20]), json.dumps(query_params)))

        graph = self.create_knn_graph(sound_ids, features=features)

        if len(graph.nodes) == 0:  # the graph does not contain any node
            return {'error': False, 'result': None, 'graph': None}

        classes, num_communities, communities, modularity = self.cluster_graph(graph)

        ratio_intra_community_edges = self._ratio_intra_community_edges(graph, communities)

        # Here we could add a step for discarding some clusters, for instance by doing:
        # graph, classes, communities, ratio_intra_community_edges = self.remove_lowest_quality_cluster(
        #         graph, classes, communities, ratio_intra_community_edges)

        node_community_centralities = self._point_centralities(graph, communities)

        # Add cluster and centralities info to graph
        nx.set_node_attributes(graph, classes, 'group')
        nx.set_node_attributes(graph, node_community_centralities, 'group_centrality')

        # Evaluation metrics vs reference features
        ami, ss, ci = self._evaluation_metrics(classes)

        end_time = time()
        logger.info('Clustering done! It took {} seconds. '
                    'Modularity: {}, '
                    'Average ratio_intra_community_edges: {}, '
                    'Average Mutual Information with reference: {}, '
                    'Silouhette Coefficient with reference: {}, '
                    'Calinski Index with reference: {}, '
                    'Davies Index with reference: {}'
                    .format(end_time-start_time, modularity, np.mean(ratio_intra_community_edges), ami, ss, ci, None))

        # Export graph as json
        graph_json = json_graph.node_link_data(graph)

        # Save results to file if SAVE_RESULTS_FOLDER is configured in clustering settings
        self._save_results_to_file(query_params, features, graph_json, sound_ids, modularity, 
                                   num_communities, ratio_intra_community_edges, ami, ss, ci, communities)

        return {'error': False, 'result': communities, 'graph': graph_json}

    def k_nearest_neighbors(self, sound_id, k):
        """Performs a K-Nearest Neighbors search on the sound given as input.

        This is currently not used, but could be useful for instance for the get similar sounds feature.

        Args: 
            sound_id (str): Sound id as query.
            k (str): number of nearest neighbors to get.

        Returns:
            str: string containing the comma-separated ids of the nearest neighbors sounds.
        """
        logger.info('Request k nearest neighbors of point {}'.format(sound_id))
        results = self.gaia.search_nearest_neighbors(sound_id, int(k))
        return json.dumps(results)

    def search_knn(self, xq, xb, k): 
        """ wrapper around the faiss knn functions without index """
        nq, d = xq.shape
        nb, d2 = xb.shape
        assert d == d2
        
        I = np.empty((nq, k), dtype='int64')
        D = np.empty((nq, k), dtype='float32')
        
        heaps = faiss.float_maxheap_array_t()
        heaps.k = k
        heaps.nh = nq
        heaps.val = faiss.swig_ptr(D)
        heaps.ids = faiss.swig_ptr(I)
        faiss.knn_L2sqr(
            faiss.swig_ptr(xq), faiss.swig_ptr(xb), 
            d, nq, nb, heaps
        )
        return D, I 