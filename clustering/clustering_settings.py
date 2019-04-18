# SERVER SETTINGS
INDEX_DIR               = '/home/xavierfav/Documents/dev/search-result-clustering/'
INDEX_NAME_AS           = 'FS_AS_embeddings_inf_60_sec_normalized' # Don't include .db extension in the names
INDEX_NAME_TAG          = 'FS_tag_features_lda_inf_60_sec_normalized'
INDEX_NAME_FS           = 'FS_selected_features_normalized_pca_inf_60_sec'
LISTEN_PORT             = 8010

# CLIENT SETTINGS (to be moved to django settings?)
CLUSTERING_ADDRESS      = 'localhost'
CLUSTERING_PORT         = 8010

# OTHER
CLUSTERING_CACHE_TIME   = 60*60*1

# FOLDER in which we save the clustering results with evaluation
SAVE_RESULTS_FOLDER     = '/home/xavierfav/Documents/dev/search-result-clustering/result_clusterings/'
# SAVE_RESULTS_FOLDER     = '/home/xavierfav/Documents/dev/search-result-clustering/result_clusterings_pruned/'