from clustering import ClusteringEngine


engine = None

default_app_config = 'clustering.apps.ClusteringConfig'


# we only init the clustering engine if running process is configured to be a Celery worker
def init_clustering_engine():
    global engine
    engine = ClusteringEngine()
