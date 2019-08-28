from clustering import ClusteringServer


engine = None

default_app_config = 'clustering.apps.ClusteringConfig'


def init_clustering_engine():
    global engine
    engine = ClusteringServer()
