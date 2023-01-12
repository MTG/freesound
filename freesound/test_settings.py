from __future__ import absolute_import
from .settings import *

postgres_username = os.getenv('FS_TEST_PG_USERNAME', None)
if postgres_username is not None:
    DATABASES['default']['NAME'] = 'freesound'
    DATABASES['default']['USER'] = postgres_username

use_django_nose = os.getenv('FS_TEST_USE_DJANGO_NOSE', None)
if use_django_nose is not None:
    INSTALLED_APPS = INSTALLED_APPS + ('django_nose',)
    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
    SOUTH_TESTS_MIGRATE = False
    NOSE_ARGS = [
        '--with-xunit',
    ]

SECRET_KEY = "testsecretwhichhastobeatleast16characterslong"
SUPPORT = (('Name Surname', 'support@freesound.org'),)
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'api_monitoring': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'clustering': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'cdn_map': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

from .logger import LOGGING
LOGGING['handlers']['stdout']['class'] = 'logging.NullHandler'

SOLR_URL = "http://fakehost:8080/fs2/"  # Avoid making accidental queries to "real" search server if running
SOLR_FORUM_URL = "http://fakehost:8080/forum/"  # Avoid making accidental requests to "real" search server if running
SEARCH_ENGINE_BACKEND_CLASS = 'utils.search.backends.solr555pysolr.Solr555PySolrSearchEngine' # Test with our own custom search engine functions
SIMILARITY_ADDRESS = 'fakehost' # Avoid making accidental requests to "real" similarity server if running
TAGRECOMMENDATION_ADDRESS = 'fakehost'  # Avoid making accidental requests to "real" tag rec server if running

# Disable debug toolbar (it will have been enabled because when importing settings and checking local_settings, the
# DISPLAY_DEBUG_TOOLBAR is most probably True, so we undo this change here)
try:
    MIDDLEWARE.remove('debug_toolbar.middleware.DebugToolbarMiddleware')
except ValueError:
    # DebugToolbarMiddleware was not enabled
    pass

try:
    INSTALLED_APPS.remove('debug_toolbar')
except ValueError:
    # debug_toolbar app was not installed
    pass
