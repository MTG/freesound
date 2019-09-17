# Clustering engine settings
clustering_settings = {
    # Gaia datasets info
    'INDEX_DIR':        '/path/to/directory/containing/gaia/dataset/files',

    # Gaia Dataset with AudioSet Features
    'INDEX_NAME_AS':    'FS_AS_embeddings_mean_max_min_nrg_normalized',  # don't include .db extension here

    # Other Gaia Datasets
    # tag-based features (Bag of Words - LDA)
    'INDEX_NAME_TAG':   None,
    # Acoustic features (selected features from Essentia extractor)
    'INDEX_NAME_FS':    None,
    # AudioCommons timbral descriptors
    'INDEX_NAME_AC':    None,

    # Maximum number of results to cluster
    'MAX_RESULTS_FOR_CLUSTERING': 1000,

    # Enable the use of the similarity gaia dataset (need to configure similarity server)
    # For development, it can be useful to use the same nearest neighbor search that is used for
    # the similar sound feature.
    'FS_SIMILARITY': False,

    # Cache settings
    # One day timeout for keeping clustering results. The cache timer is reset when the clustering is 
    # requested so that popular queries that are performed once a day minimum will always stay in cache
    # and won't be recomputed.
    'CLUSTERING_CACHE_TIME':            24*60*60*1,
    # One minute timeout for keeping the pending state. When a clustering is being performed async in a 
    # Celery worker, we consider the clustering as pending for only 1 minute. This may be useful if a 
    # worker task got stuck. There should be a settings in celery to stop a worker task if it is running 
    # for too long.
    'CLUSTERING_PENDING_CACHE_TIME':    60*1,

    # Folder for saving the clustering results with evaluation (dev/debug/research purpose)
    'SAVE_RESULTS_FOLDER': None,
}
