from sklearn.cluster import KMeans
from sklearn.cluster import AffinityPropagation
from sklearn.cluster import MeanShift, estimate_bandwidth
from sklearn.cluster import spectral_clustering
#from sklearn.cluster import AgglomerativeClustering
from sklearn.cluster import DBSCAN
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn import metrics
import networkx as nx
import community.community_louvain as com
import numpy as np
import operator
from sklearn.datasets.samples_generator import make_blobs
from sklearn.metrics.pairwise import euclidean_distances


def kmeans(data, n_clusters=5):
    km = KMeans(n_clusters=n_clusters, init='k-means++', max_iter=200, n_init=1)
    km.fit(data)
    return km.labels_

def affinityPropagation(data, preference=-50):
    af = AffinityPropagation(preference=preference)
    af.fit(data)
    return af.labels_

def meanShift(data):
    bandwidth = estimate_bandwidth(data, quantile=1)
    ms = MeanShift(bandwidth=bandwidth, bin_seeding=True)
    ms.fit(data)
    return ms.labels_

def spectral(similarity_matrix):
    labels = spectral_clustering(similarity_matrix)
    return labels

def dbscan(data):
    db = DBSCAN(eps=0.3, min_samples=10)
    db.fit(data)
    return db.labels_

def agglomerative(data):
    # check here how to return the labels
    Z = linkage(data, 'ward')
    return Z

def clusters_to_classes(clusters):
    # for networkx>2 community detection algorithm
    clusters = list(clusters)
    classes = np.zeros(sum([len(cluster) for cluster in clusters]))
    for idx, cluster in enumerate(clusters):
        for i in cluster:
            classes[i] = idx
    return classes

def knnGraph(similarity_matrix, k):
    graph = create_knn_graph(similarity_matrix, k)
#    clusters = nx.algorithms.community.asyn_fluidc(graph, k)
#    return clusters_to_classes(clusters)
#    the community module works only for networkx<2
    classes = com.best_partition(graph)
    return [classes[k] for k in range(len(classes.keys()))]

def knnWeightedGraph(similarity_matrix, k, threshold=0.1):
    graph = create_knn_weighted_graph(similarity_matrix, k, threshold)
#    clusters = nx.algorithms.community.asyn_fluidc(graphm )
#    return clusters_to_classes(clusters)
#    the community module works only for networkx<2
    classes = com.best_partition(graph)
    return [classes[k] for k in range(len(classes.keys()))]

def create_knn_graph(similarity_matrix, k):
    """ Returns a knn graph from a similarity matrix - NetworkX module """
    np.fill_diagonal(similarity_matrix, 0) # for removing the 1 from diagonal
    g = nx.Graph()
    g.add_nodes_from(range(len(similarity_matrix)))
    for idx in range(len(similarity_matrix)):
        g.add_edges_from([(idx, i) for i in nearest_neighbors(similarity_matrix, idx, k)])
    return g  

def create_knn_weighted_graph(similarity_matrix, k, threshold=0.1):
    """ Returns a knn weigthed graph from a similarity matrix - NetworkX module """
    np.fill_diagonal(similarity_matrix, 0) # for removing the 1 from diagonal
    g = nx.Graph()
    g.add_nodes_from(range(len(similarity_matrix)))
    for idx in range(len(similarity_matrix)):
        #g.add_edges_from([(idx, i) for i in self.nearest_neighbors(similarity_matrix, idx, k) if similarity_matrix[idx][i] > threshold])
        #g.add_weighted_edges_from([(idx, i[0], i[1]) for i in zip(range(len(similarity_matrix)), similarity_matrix[idx]) if                 i[0] != idx and i[1] > threshold])
        g.add_weighted_edges_from([(idx, i, similarity_matrix[idx][i]) for i in nearest_neighbors(similarity_matrix, idx, k) if similarity_matrix[idx][i] > threshold])
        #print idx, self.nearest_neighbors(similarity_matrix, idx, k)
    return g
    
def nearest_neighbors(similarity_matrix, idx, k):
    distances = []
    for x in range(len(similarity_matrix)):
        distances.append((x,similarity_matrix[idx][x]))
    distances.sort(key=operator.itemgetter(1), reverse=True)
    return [d[0] for d in distances[0:k]]    
 
#X, y = make_blobs(n_samples=10, centers=10, n_features=2, random_state=0)
#similarity = euclidean_distances(X)

def purity_score(y_true, y_pred):
    # matrix which will hold the majority-voted labels
    y_labeled_voted = np.zeros(y_true.shape)
    labels = np.unique(y_true)
    # We set the number of bins to be n_classes+2 so that 
    # we count the actual occurence of classes between two consecutive bin
    # the bigger being excluded [bin_i, bin_i+1[
    bins = np.concatenate((labels, [np.max(labels)+1]), axis=0)

    for cluster in np.unique(y_pred):
        hist, _ = np.histogram(y_true[y_pred==cluster], bins=bins)
        # Find the most present label in the cluster
        winner = np.argmax(hist)
        y_labeled_voted[y_pred==cluster] = winner

    return metrics.accuracy_score(y_true, y_labeled_voted)

def evaluate(labels_true, labels):
#    homogeneity = metrics.homogeneity_score(labels_true, labels)
#    completeness = metrics.completeness_score(labels_true, labels)
#    v_measure = metrics.v_measure_score(labels_true, labels)
    adjusted_rand = metrics.adjusted_rand_score(labels_true, labels)
    adjusted_mutual_info = metrics.adjusted_mutual_info_score(labels_true, labels)
#    normalized_mutual_info = metrics.normalized_mutual_info_score(labels_true, labels)
    purity = purity_score(labels_true, labels)
    
    return round(purity, 4), round(adjusted_mutual_info, 4), round(adjusted_rand,4)