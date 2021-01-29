# -*- coding: utf-8 -*-

import os

DEBUG = True
DISPLAY_DEBUG_TOOLBAR = True

# Set support param so contact form does not fail
SUPPORT = (('Name Surname', 'support@freesound.org'),)

# Data path of the mounted data volume in docker
DATA_PATH = '/freesound-data/'

# Use email file backend
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '../freesound-data/')), "_mail/")


WORKER_MIN_FREE_DISK_SPACE_PERCENTAGE = 0.0
BULK_UPLOAD_MIN_SOUNDS = 0

# Sentry DSN configuration
SENTRY_DSN = None
