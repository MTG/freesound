# -*- coding: utf-8 -*-

DEBUG = True
DISPLAY_DEBUG_TOOLBAR = True

ADMINS = (
    ('Your Email Here', 'abc@gmail.com'),
)
MANAGERS = ADMINS

# If ALLOWED emails is not empty, only emails going to these destinations will be actually sent
ALLOWED_EMAILS = []

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',  # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

EMAIL_HOST = 'localhost'
EMAIL_PORT = 2525

PROXIES = {} #'http': 'http://proxy.upf.edu:8080'}

RECAPTCHA_PRIVATE_KEY = '6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe'
RECAPTCHA_PUBLIC_KEY = '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI'
AKISMET_KEY = ''

GOOGLE_API_KEY = ''
GOOGLE_ANALYTICS_KEY = ''

USE_ZENDESK_FOR_SUPPORT_REQUESTS = False
ZENDESK_EMAIL = ''
ZENDESK_TOKEN = ''

SOLR_URL = "http://localhost:8983/solr/fs2/"
SOLR_FORUM_URL = "http://localhost:8983/solr/forum/"

GEARMAN_JOB_SERVERS = ["localhost:4730"]


STRIPE_KEY = "sk_test_..."
PAYPAL_EMAIL = "paypal@freesound.org"
PAYPAL_VALIDATION_URL = "https://www.sandbox.paypal.com/cgi-bin/webscr"
DONATIONS_PER_PAGE = 40

GRAYLOG_USERNAME = "apiuser"
GRAYLOG_PASSWORD = "apiuserpassword"

# To customize DATA_URL
# DATA_URL = "https://freesound.org/data/"

# To customize DATA_PATH
'''
import os
DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../freesound-data/')) # overriding settings
AVATARS_PATH = os.path.join(DATA_PATH, "avatars/")
PREVIEWS_PATH = os.path.join(DATA_PATH, "previews/")
DISPLAYS_PATH = os.path.join(DATA_PATH, "displays/") # waveform and spectrum views
SOUNDS_PATH = os.path.join(DATA_PATH, "sounds/")
PACKS_PATH = os.path.join(DATA_PATH, "packs/")
UPLOADS_PATH = os.path.join(DATA_PATH, "uploads/")
ANALYSIS_PATH = os.path.join(DATA_PATH, "analysis/")
'''

# SOLR ranking weights
DEFAULT_SEARCH_WEIGHTS = {
    'id' : 4,
    'tag' : 4,
    'description' : 3,
    'username' : 1,
    'pack_tokenized' : 2,
    'original_filename' : 2
}

APIV2_BASIC_THROTTLING_RATES_PER_LEVELS = {
    0: ['0/minute', '0/day', '0/hour'],  # Client 'disabled'
    1: ['60/minute', '2000/day', None],  # Ip limit not yet enabled
    2: ['300/minute', '5000/day', None],  # Ip limit not yet enabled
    99: [],  # No limit of requests
}

APIV2_POST_THROTTLING_RATES_PER_LEVELS = {
    0: ['0/minute', '0/day',  '0/hour'],  # Client 'disabled'
    1: ['30/minute', '500/day', None],  # Ip limit not yet enabled
    2: ['60/minute', '1000/day', None],  # Ip limit not yet enabled
    99: [],  # No limit of requests
}

# Sentry

RAVEN_CONFIG = {
    'dsn': 'DSN_PROVIDED_BY_SENTRY',
}
