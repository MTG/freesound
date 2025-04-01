#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

from __future__ import absolute_import
from __future__ import division

from builtins import str
from builtins import zip
from builtins import range
from builtins import object
from past.utils import old_div
import json
import logging
import os
from django.conf import settings
import six
from time import time

import community as com
import numpy as np
import networkx as nx
from networkx.readwrite import json_graph
from networkx.algorithms.community import k_clique_communities, greedy_modularity_communities
from sklearn import metrics
from sklearn.feature_selection import mutual_info_classif
from sklearn.neighbors import kneighbors_graph


logger = logging.getLogger('clustering')


class ClusteringEngine(object):
    """Clustering Engine class.

    This class regroups various methods for performing clustering on a set of sounds.

    Instead of directly using the audio feature space for performing the clustering, it creates a 
    K-Nearest Neighbors Graph that is then partitioned for obtaining the clusters.
    The available features used for clustering are listed in the clustering_settings.py file.

    It also includes some methods that enable to automaticaly estimate the performance of the clustering
    method. Moreover, a few unsued alternative methods for performing some intermediate steps are left 
    here for developement and research purpose.
    """

    def _prepare_clustering_result_and_reference_features_for_evaluation(self, partition):
        """Formats the clustering classes and some reference features in order to then estimate how good is the 
        clustering performance. Tipically the reference features can be tag-derived features that reflect semantic 
        characteristics of the content. The reference features are defined in the clustering settings file.
        
        Extracts reference features for the sounds given as keys of the partition argument.
        Prepares classes and extracted features in lists in order to compare them.
        Removes sounds with missing features.

        Args:
            partition (Dict{Int: Int}): clustering classes for each sound {<sound_id>: <class_idx>}.

        Returns:
            Tuple(List[List[Float]], List[Int]): 2-element tuple containing a list of evaluation features 
                and list of classes (clusters) idx.
        """
        sound_ids_list, clusters = list(partition.keys()), list(partition.values())
        reference_features = self.feature_store.return_sound_reference_features(sound_ids_list)

        # Remove sounds that are not in the reference dataset
        idx_to_remove = set([idx for idx, feature in enumerate(reference_features) if feature is None])
        reference_features_filtered = [f for idx, f in enumerate(reference_features) if idx not in idx_to_remove]
        clusters_filtered = [c for idx, c in enumerate(clusters) if idx not in idx_to_remove]

        return reference_features_filtered, clusters_filtered

    def _average_mutual_information_reference_features_clusters(self, partition):
        """Estimates Average Mutual Information between reference features and the given clustering classes.

        Args:
            partition (Dict{Int: Int}): clustering classes for each sound {<sound_id>: <class_idx>}.

        Returns:
            Numpy.float: Average Mutual Information.
        """
        reference_features, clusters = self._prepare_clustering_result_and_reference_features_for_evaluation(partition)
        return np.average(mutual_info_classif(reference_features, clusters, discrete_features=True))

    def _silouhette_coeff_reference_features_clusters(self, partition):
        """Computes mean Silhouette Coefficient score between reference features and the given clustering classes.

        Args:
            partition (Dict{Int: Int}): clustering classes for each sound {<sound_id>: <class_idx>}.

        Returns:
            Numpy.float: mean Silhouette Coefficient.
        """
        reference_features, clusters = self._prepare_clustering_result_and_reference_features_for_evaluation(partition)
        return metrics.silhouette_score(reference_features, clusters, metric='euclidean')

    def _calinski_idx_reference_features_clusters(self, partition):
        """Computes the Calinski and Harabaz score between reference features and the given clustering classes.

        Args:
            partition (Dict{Int: Int}): clustering classes for each sound {<sound_id>: <class_idx>}.

        Returns:
            Numpy.float: Calinski and Harabaz score.
        """
        reference_features, clusters = self._prepare_clustering_result_and_reference_features_for_evaluation(partition)
        return metrics.calinski_harabaz_score(reference_features, clusters)
    
    def _davies_idx_reference_features_clusters(self, partition):
        """Computes the Davies-Bouldin score between reference features and the given clustering classes.

        Args:
            partition (Dict{Int: Int}): clustering classes for each sound {<sound_id>: <class_idx>}.

        Returns:
            Numpy.float: Davies-Bouldin score.
        """
        # This metric is not included in current used sklearn version
        reference_features, clusters = self._prepare_clustering_result_and_reference_features_for_evaluation(partition)
        return metrics.davies_bouldin_score(reference_features, clusters)

    def _evaluation_metrics(self, partition):
        """Computes different scores related to the clustering performance by comparing the resulting clustering classes
        to the reference features defined in the clustering settings file. The reference features tipically correspond to 
        tag-derived features that can reflect semantic characteristics of the audio clips.

        Args:
            partition (Dict{Int: Int}): clustering classes for each sound {<sound_id>: <class_idx>}.

        Returns:
            Tuple(Numpy.float, Numpy.float, Numpy.float): 3-element tuple containing the Average Mutual Information
                score, the Silhouette Coefficient and the Calinski and Harabaz score.
        """
        # we compute the evaluation metrics only if some reference features are available for evaluation
        # we return None when they are not available not to break the following part of the code
        '''
        # NOTE: the following code is commented because the reference features are not available in the current version of the code
        # If in the future we wan to perform further evaluation, we should re-implement some of these functions
        if clust_settings.REFERENCE_FEATURES in clust_settings.AVAILABLE_FEATURES:
            reference_features, clusters = self._prepare_clustering_result_and_reference_features_for_evaluation(partition)
            ami = np.average(mutual_info_classif(reference_features, clusters, discrete_features=True))
            ss = metrics.silhouette_score(reference_features, clusters, metric='euclidean')
            ci = metrics.calinski_harabaz_score(reference_features, clusters)
            return ami, ss, ci
        else:
            return None, None, None
        '''
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
        node_community_centralities = {k: old_div(v,max(d.values())) for d in communities_centralities for k, v in d.items()}

        return node_community_centralities

    def create_knn_graph(self, sound_ids_list, similarity_vectors_map):
        """Creates a K-Nearest Neighbors Graph representation of the given sounds.

        Args:
            sound_ids_list (List[str]): list of sound ids.
            similarity_vectors_map (Dict{int:List[float]}): dictionary with the similarity feature vectors for each sound.

        Returns:
            (nx.Graph): NetworkX graph representation of sounds.
        """
        # Create k nearest neighbors graph        
        graph = nx.Graph()
        graph.add_nodes_from(sound_ids_list)
        # we set k to log2(N), where N is the number of elements to cluster. This allows us to reach a sufficient number of 
        # neighbors for small collections, while limiting it for larger collections, which ensures low-computational complexity.
        k = int(np.ceil(np.log2(len(sound_ids_list))))

        features = []
        sound_ids_out = []
        for sound_id, feature_vector in similarity_vectors_map.items():
            features.append(feature_vector)
            sound_ids_out.append(sound_id)            
        sound_features = np.array(features).astype('float32')

        A = kneighbors_graph(sound_features, k)
        for idx_from, (idx_to, distance) in enumerate(zip(A.indices, A.data)):
            idx_from = int(idx_from / k)
            if distance < settings.CLUSTERING_MAX_NEIGHBORS_DISTANCE:
                graph.add_edge(sound_ids_out[idx_from], sound_ids_out[idx_to])

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
        partition  = com.best_partition(graph)
        num_communities = max(partition.values()) + 1
        communities = [[key for key, value in six.iteritems(partition ) if value == i] for i in range(num_communities)]

        # overall quality (modularity of the partition)
        modularity = com.modularity(partition , graph)

        return partition, num_communities, communities, modularity
    
    def cluster_graph_overlap(self, graph, k=5):
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
        num_communities = len(communities)
        partition = {sound_id: cluster_id for cluster_id, cluster in enumerate(communities) for sound_id in cluster}

        return  partition, num_communities, communities, None
    
    def remove_lowest_quality_cluster(self, graph, partition, communities, ratio_intra_community_edges):
        """Removes the lowest quality cluster in the given graph.

        Discards the cluster that has the lowest ratio of the number of intra-community edges. Removes the related values 
        of the removed cluster from the given clustering information.

        Args:
            graph (nx.Graph): NetworkX graph representation of sounds.
            partition (Dict{Int: Int}): clustering classes for each sound {<sound_id>: <class_idx>}.
            communities (List[List[Int]]): List storing Lists containing the Sound ids that are in each community (cluster).
            ratio_intra_community_edges (List[Float]): intra-community edges ratio.

        Returns:
            Tuple(nx.Graph, Dict{Int: Int}, List[List[Int]], List[float]): 4-element tuple containing the graph representation 
            of the sounds, the clustering classes for each sound {<sound_id>: <class_idx>}, the sound ids in the communities 
            and the ratio of intra-community edges in each cluster.
        """
        # if two clusters or less, we do not remove any
        if len(communities) <= 2:
            return graph, partition, communities, ratio_intra_community_edges
        min_ratio_idx = np.argmin(ratio_intra_community_edges)
        sounds_to_remove = communities[min_ratio_idx]
        graph.remove_nodes_from(sounds_to_remove)
        del communities[min_ratio_idx]
        for snd in sounds_to_remove:
            del partition[snd]
        del ratio_intra_community_edges[min_ratio_idx]
        for idx in range(min_ratio_idx, max(partition.values())):
            for snd in communities[idx]:
                partition[snd] -= 1
        return graph, partition, communities, ratio_intra_community_edges

    def cluster_points(self, query_params, sound_ids, similarity_vectors_map):
        """Applies clustering on the requested sounds using the given features name.

        Args:
            query_params (str): string representing the query parameters submited by the user to the search engine.
            sound_ids (List[int]): list containing the ids of the sound to cluster.
            similarity_vectors_map (Dict{int:List[float]}): dictionary with the similarity feature vectors for each sound.
        
        Returns:
            Dict: contains the resulting clustering classes and the graph in node-link format suitable for JSON serialization.
        """
        start_time = time()
        sound_ids = [str(s) for s in sound_ids]
        logger.info('Request clustering of {} points: {} ... from the query "{}"'
                .format(len(sound_ids), ', '.join(sound_ids[:20]), json.dumps(query_params)))

        graph = self.create_knn_graph(sound_ids, similarity_vectors_map=similarity_vectors_map)

        if len(graph.nodes) == 0:  # the graph does not contain any node
            return {'clusters': None, 'graph': None}

        partition, num_communities, communities, modularity = self.cluster_graph(graph)

        ratio_intra_community_edges = self._ratio_intra_community_edges(graph, communities)

        # Discard low quality cluster if there are more than NUM_MAX_CLUSTERS clusters
        num_exceeding_clusters = num_communities - settings.CLUSTERING_NUM_MAX_CLUSTERS
        if num_exceeding_clusters > 0:
            for _ in range(num_exceeding_clusters):
                graph, partition, communities, ratio_intra_community_edges = self.remove_lowest_quality_cluster(
                    graph, partition, communities, ratio_intra_community_edges
                )

        node_community_centralities = self._point_centralities(graph, communities)

        # Add cluster and centralities info to graph
        nx.set_node_attributes(graph, partition, 'group')
        nx.set_node_attributes(graph, node_community_centralities, 'group_centrality')

        # Evaluation metrics vs reference features
        ami, ss, ci = self._evaluation_metrics(partition)

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

        return {'clusters': communities, 'graph': graph_json}
