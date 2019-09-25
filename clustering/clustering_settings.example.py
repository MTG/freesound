# Directory where the Gaia dataset index files are located.
INDEX_DIR = '/home/xavierfav/Documents/dev/search-result-clustering/'

# Configuration of the features used for clustering or evaluation.
# We define here for each features the Gaia dataset index file, the descriptor name within the dataset 
# and the metric used for similarity computation
AVAILABLE_FEATURES = {
    # AudioSet Features (feature vector of the frame of max energy)
    'AUDIOSET_FEATURES': {
        'DATASET_FILE': 'FS_AS_embeddings_mean_max_min_nrg_normalized',
        'GAIA_DESCRIPTOR_NAMES': 'AS_embeddings_ppc_max_energy',
        'GAIA_METRIC': 'euclidean'
    },
    # tag-based features (Bag of Words - LDA)
    'TAG_DERIVED_FEATURES': None,

    # Acoustic features (selected features from Essentia extractor - PCA)
    'FREESOUND_EXTRACTOR_SELECTED_FEATURES': None,

    # AudioCommons timbral descriptors
    'AC_TIMBRAL_FEATURES': None,
}

# Default features used for clustering
DEFAULT_FEATURES = 'AUDIOSET_FEATURES'

# Tag-derived features used for clustering evaluation
TAG_FEATURES = None

# Maximum number of results to cluster
MAX_RESULTS_FOR_CLUSTERING = 1000

# Cache settings
# One day timeout for keeping clustering results. The cache timer is reset when the clustering is 
# requested so that popular queries that are performed once a day minimum will always stay in cache
# and won't be recomputed.
CLUSTERING_CACHE_TIME = 24*60*60*1
# One minute timeout for keeping the pending state. When a clustering is being performed async in a 
# Celery worker, we consider the clustering as pending for only 1 minute. This may be useful if a 
# worker task got stuck. There should be a settings in celery to stop a worker task if it is running 
# for too long.
CLUSTERING_PENDING_CACHE_TIME = 60*1

# Folder for saving the clustering results with evaluation (dev/debug/research purpose)
SAVE_RESULTS_FOLDER = None
