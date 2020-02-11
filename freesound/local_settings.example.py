# -*- coding: utf-8 -*-

import os

DEBUG = True
DISPLAY_DEBUG_TOOLBAR = True


# Use email file backend
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '../freesound-data/')), "_mail/")

# Use cache file backend
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache', # 'django.core.cache.backends.dummy.DummyCache',  # 'django.core.cache.backends.locmem.LocMemCache',  #
        'LOCATION': os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '../freesound-data/')), "_cache/"),
    }
}

WORKER_MIN_FREE_DISK_SPACE_PERCENTAGE = 0.0
BULK_UPLOAD_MIN_SOUNDS = 0
