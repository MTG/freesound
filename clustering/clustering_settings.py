# SERVER SETTINGS
INDEX_DIR   = '/home/xavierfav/Documents/dev/search-result-clustering/'
INDEX_NAME  = 'FS_dev_sounds_normalized' # Don't include .db extension in the name here
LISTEN_PORT = 8010

# CLIENT SETTINGS (to be moved to django settings?)
CLUSTERING_ADDRESS               = 'localhost'
CLUSTERING_PORT                  = 8010

# OTHER
CLUSTERING_CACHE_TIME = 60*60*1
