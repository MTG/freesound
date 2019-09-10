# Clustering engine settings
clustering_settings = {
    # Gaia datasets info
    'INDEX_DIR':        '/path/to/directory/containing/gaia/dataset/files',
    'INDEX_NAME_AS':    'FS_AS_embeddings_mean_max_min_nrg_normalized',  # don't include .db extension here

    # Enable the use of the similarity gaia dataset (need to configure similarity server)
    'FS_SIMILARITY': False,

    # Cache settings
    'CLUSTERING_CACHE_TIME':            24*60*60*1,  # one day timeout for keeping clustering results
    'CLUSTERING_PENDING_CACHE_TIME':    60*1,        # one minute timeout for keeping the pending state

    # Folder for saving the clustering results with evaluation (dev/debug/research purpose)
    'SAVE_RESULTS_FOLDER': None,
}
