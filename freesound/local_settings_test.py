from settings import *

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}