from clustering import ClusteringEngine


engine = None

default_app_config = 'clustering.apps.ClusteringConfig'

# strings used for communicating the state of the clustering process
CLUSTERING_RESULT_STATUS_PENDING = "pending"
CLUSTERING_RESULT_STATUS_FAILED = "failed"

# We only init the clustering engine (which requires specific dependencies) if running process 
# is configured to be a Celery worker. This function is called when Django starts in the ready 
# method of the clustering app.
def init_clustering_engine():
    global engine
    engine = ClusteringEngine()
