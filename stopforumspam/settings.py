from django.conf import settings

CACHE_EXPIRE = getattr(settings, 'SFS_CACHE_EXPIRE', 1) #days
LOG_EXPIRE = getattr(settings, 'SFS_LOG_EXPIRE', 1) #days

# Inserted in Log model at every update
LOG_MESSAGE_UPDATE = getattr(settings, 'SFS_LOG_MESSAGE_UPDATE', u'Log updated from stopforumspam.com')

# Check all post requests
ALL_POST_REQUESTS = getattr(settings, 'SFS_ALL_POST_REQUESTS', False)

# Used if ALL_POST_REQUESTS=True
URLS_IGNORE = getattr(settings, 'SFS_URLS_IGNORE', [])
# Example: ["name_of_view", "/url/path/"]

# Used if ALL_POST_REQUESTS=False
URLS_INCLUDE = getattr(settings, 'SFS_URLS_INCLUDE', [])
# Example: ["name_of_view", "/url/path/"]

SOURCE_ZIP = getattr(settings, 'SFS_SOURCE_ZIP', "http://www.stopforumspam.com/downloads/listed_ip_7.zip")
ZIP_FILENAME = getattr(settings, 'SFS_ZIP_FILENAME', "listed_ip_7.txt")

# Used for testing!
FORCE_ALL_REQUESTS = getattr(settings, 'SFS_FORCE_ALL_REQUESTS', False)

LOG_SPAM = getattr(settings, 'SFS_LOG_SPAM', True)
