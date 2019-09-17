from clustering import ClusteringEngine


engine = None

default_app_config = 'clustering.apps.ClusteringConfig'

# strings used for communicating the state of the clustering process
CLUSTERING_RESULT_STATUS_PENDING = "pending"
CLUSTERING_RESULT_STATUS_FAILED = "failed"

# we only init the clustering engine if running process is configured to be a Celery worker
def init_clustering_engine():
    global engine
    engine = ClusteringEngine()
