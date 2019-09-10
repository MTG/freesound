# Clustering engine settings
clustering_settings = {
    # Gaia datasets info
    'INDEX_DIR':        '/home/xavierfav/Documents/dev/search-result-clustering/',
    # 'INDEX_NAME_AS':    'FS_AS_embeddings_inf_60_sec_normalized',  # don't include .db extension here
    'INDEX_NAME_AS':    'FS_AS_embeddings_mean_max_min_nrg_normalized',
    'INDEX_NAME_TAG':   'FS_tag_features_lda_inf_60_sec_normalized',
    'INDEX_NAME_FS':    'FS_selected_features_normalized_pca_inf_60_sec',
    'INDEX_NAME_AC':    'FS_AC_descriptors_normalized',

    # Enable the use of the similarity gaia dataset (need to configure similarity server)
    'FS_SIMILARITY': False,

    # Cache settings
    'CLUSTERING_CACHE_TIME':            24*60*60*1,  # one day timeout for keeping clustering results
    'CLUSTERING_PENDING_CACHE_TIME':    60*1,        # one minute timeout for keeping the pending state

    # Folder for saving the clustering results with evaluation (dev/debug/research purpose)
    # 'SAVE_RESULTS_FOLDER': '/home/xavierfav/Documents/dev/search-result-clustering/result_clusterings/',
    # 'SAVE_RESULTS_FOLDER': '/home/xavierfav/Documents/dev/search-result-clustering/result_clusterings_pruned/',
}
