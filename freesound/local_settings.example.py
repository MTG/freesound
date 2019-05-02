# -*- coding: utf-8 -*-


# -------------------------------------------------------------------------------
# Required Django settings

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}


# -------------------------------------------------------------------------------
# Some default configurations for development (no need to make changes here)

DEBUG = True
DISPLAY_DEBUG_TOOLBAR = True

SECRET_KEY = 'thisisasecretkey'

# Default SOLR URLs if running locally
SOLR_URL = "http://localhost:8983/solr/fs2/"
SOLR_FORUM_URL = "http://localhost:8983/solr/forum/"

# Default Gearman hostname:port if running locally
GEARMAN_JOB_SERVERS = ["localhost:4730"]

# Set data URL to production Freesound as data files will not likely be in local
DATA_URL = "https://freesound.org/data/"

WORKER_MIN_FREE_DISK_SPACE_PERCENTAGE = 0.0

import os
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '_mail'))

BULK_UPLOAD_MIN_SOUNDS = 0
