# -*- coding: utf-8 -*-

DEBUG = True
DISPLAY_DEBUG_TOOLBAR = True

ADMINS = (
    ('Your Email Here', 'abc@gmail.com'),
)

# If ALLOWED emails is not empty, only emails going to these destinations will be actually sent
ALLOWED_EMAILS = []

DATABASE_ENGINE = 'django.db.backends.postgresql_psycopg2' # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'freesound'             # Or path to database file if using sqlite3.
DATABASE_USER = 'freesound'             # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.
DATABASE_PASSWORD = ''

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

EMAIL_HOST = 'localhost'
EMAIL_PORT = 2525

PROXIES = {} #'http': 'http://proxy.upf.edu:8080'}

RECAPTCHA_PRIVATE_KEY = ''
RECAPTCHA_PUBLIC_KEY = ''
AKISMET_KEY = ''

GOOGLE_API_KEY = ''
GOOGLE_ANALYTICS_KEY = ''

SOLR_URL = "http://localhost:8983/solr/fs2/"
SOLR_FORUM_URL = "http://localhost:8983/solr/forum/"

GEARMAN_JOB_SERVERS = ["localhost:4730"]

PLEDGIE_CAMPAIGN=14560

LOG_CLICKTHROUGH_DATA = False

# SOLR ranking weights
DEFAULT_SEARCH_WEIGHTS = {
    'id' : 4,
    'tag' : 4,
    'description' : 3,
    'username' : 1,
    'pack_tokenized' : 2,
    'original_filename' : 2
}

# APIv2 throttling limits
# Define Api usage limit rates per defined throttling levels
# Possible time units: second, minute, hour or day
# Every level must include three limits, a burst limit, a sustained limit andan ip which are checked separately
# Burst limit sets the maximum number of requests that an api client can do in a minute
# Sustained limit sets the maximum number of requests that an api client can do in a day
# Ip limit sets the maximum number of requests from different ips that a client can do in an hour

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