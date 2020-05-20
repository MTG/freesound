# -*- coding: utf-8 -*-

import os
import datetime
import re
import logging.config
import dj_database_url
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# -------------------------------------------------------------------------------
# Miscellaneous Django settings

DEBUG = False
DISPLAY_DEBUG_TOOLBAR = False

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '___this_is_a_secret_key_that_should_not_be_used___')

default_url = 'postgres://postgres@db/postgres'
DATABASES = {'default': dj_database_url.config('DJANGO_DATABASE_URL', default=default_url)}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'silk.middleware.SilkyMiddleware',
    'freesound.middleware.TosAcceptanceHandler',
    'freesound.middleware.BulkChangeLicenseHandler',
    'freesound.middleware.UpdateEmailHandler',
    'freesound.middleware.OnlineUsersHandler',
    'corsheaders.middleware.CorsMiddleware',
    'freesound.middleware.FrontendPreferenceHandler',
]

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.flatpages',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'messages.apps.MessagesConfig',
    'apiv2',
    'geotags',
    'accounts',
    'ratings',
    'tags',
    'general.apps.GeneralConfig',
    'support',
    'wiki',
    'favorites',
    'sounds',
    'comments',
    'bookmarks',
    'forum',
    'search',
    'django_extensions',
    'tickets',
    'gunicorn',
    'oauth2_provider',
    'rest_framework',
    'corsheaders',
    'follow',
    'fixture_magic',
    'utils',
    'donations',
    'monitor',
    'django_object_actions',
    'silk',
]

# Silk is the Request/SQL logging platform. We install it but leave it disabled
# It can be activated in local_settings by changing INTERCEPT_FUNC
SILKY_AUTHENTICATION = True  # User must login
SILKY_AUTHORISATION = True  # User must have permissions
SILKY_PERMISSIONS = lambda user: user.is_superuser
SILKY_INTERCEPT_FUNC = lambda request: False

CORS_ORIGIN_ALLOW_ALL = True

AUTHENTICATION_BACKENDS = ('accounts.modelbackend.CustomModelBackend',)

# This was the default serializer in django 1.6. Now we keep using it because
# we saw some erros when running tests, in the future we should change to the
# new one.
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

TIME_ZONE = 'Europe/Brussels'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_X_FORWARDED_HOST = True

# Not using django timezones as project originally with Django 1.3. We might fix this in the future:
# https://docs.djangoproject.com/en/1.5/topics/i18n/timezones/#time-zones-migration-guide
USE_TZ = False

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = 'freesound'

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

ROOT_URLCONF = 'freesound.urls'

WSGI_APPLICATION = 'freesound.wsgi.application'

LOGIN_URL = '/home/login/'
LOGOUT_URL = '/home/logout/'
LOGIN_REDIRECT_URL = '/home/'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')

IGNORABLE_404_URLS = (
    # for each <prefix> in IGNORABLE_404_STARTS
    re.compile(r'^/cgi-bin/'),
    re.compile(r'^/_vti_bin'),
    re.compile(r'^/_vti_inf'),
    re.compile(r'^/favicon'),
    # for each <suffix> in IGNORABLE_404_ENDS
    re.compile(r'.jsp$'),
    re.compile(r'mail.pl$'),
    re.compile(r'mailform.pl$'),
    re.compile(r'mail.cgi$'),
    re.compile(r'mailform.cgi$'),
    re.compile(r'.php$'),
    re.compile(r'similar$'),
)

ALLOWED_HOSTS = ['*']

# Silence Django system check urls.W002 "Your URL pattern '/$' has a regex beginning with a '/'.
# Remove this slash as it is unnecessary." triggered in API urls. Although the check claims the last
# slash is not necessary, it is in our case as otherwise it breaks some API urls when these don't end
# with slash.
SILENCED_SYSTEM_CHECKS = ['urls.W002']

INTERNAL_IPS = ['127.0.0.1']

MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
]


# -------------------------------------------------------------------------------
# Email settings

SERVER_EMAIL = 'noreply@freesound.org'
EMAIL_SUBJECT_PREFIX = '[freesound] '
DEFAULT_FROM_EMAIL = 'Freesound NoReply <noreply@freesound.org>'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25

# AWS tokens (for accessing email bounce list and email statistics)
AWS_REGION = ''
AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''

# Email bounce processing parameters
AWS_SQS_QUEUE_URL = ''
AWS_SQS_MESSAGES_PER_CALL = 1  # between 1 and 10, see accounts management command `process_email_bounces` for more

# Email stats retrieval parameters (see utils.aws.report_ses_stats for more details)
AWS_SES_BOUNCE_RATE_SAMPLE_SIZE = 10500  # should be ~ 10000-11000
AWS_SES_SHORT_BOUNCE_RATE_DATAPOINTS = 4  # cron period (1hr) / AWS stats period (15min)

# If ALLOWED emails is not empty, only emails going to these destinations will be actually sent
ALLOWED_EMAILS = []


# -------------------------------------------------------------------------------
# Media paths, URLS and static settings

# Absolute path to the directory that holds media (e.g. /home/media/media.lawrence.com/)
MEDIA_ROOT = os.path.join(os.path.dirname(__file__), '../freesound/../media')
MEDIA_URL = "/media/"

# Add freesound/static/ to STATICFILES_DIRS as it won't be added by default (freesound/ is not an installed Django app)
STATICFILES_DIRS = [os.path.join(os.path.dirname(__file__), 'static'), ]
STATIC_URL = '/static/'
STATIC_ROOT = 'bw_static'
STATICFILES_STORAGE = 'freesound.storage.NoStrictManifestStaticFilesStorage'


# -------------------------------------------------------------------------------
# Freesound miscellaneous settings

SUPPORT = ()

IFRAME_PLAYER_SIZE = {
        'large': [920, 245],
        'medium': [481, 86],
        'small': [375, 30],
        'twitter_card': [440, 132]
    }

FREESOUND_RSS = ''

# Number of things per page
FORUM_POSTS_PER_PAGE = 20
FORUM_THREADS_PER_PAGE = 40
SOUND_COMMENTS_PER_PAGE = 5
SOUNDS_PER_PAGE = 15
PACKS_PER_PAGE = 15
REMIXES_PER_PAGE = 10
MAX_TICKETS_IN_MODERATION_ASSIGNED_PAGE = 30
SOUNDS_PER_DESCRIBE_ROUND = 10
SOUNDS_PENDING_MODERATION_PER_PAGE = 8
MAX_UNMODERATED_SOUNDS_IN_HOME_PAGE = 5
DONATIONS_PER_PAGE = 40

# User flagging notification thresholds
USERFLAG_THRESHOLD_FOR_NOTIFICATION = 3
USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING = 6

ALLOWED_AUDIOFILE_EXTENSIONS = ['wav', 'aiff', 'aif', 'ogg', 'flac', 'mp3', 'm4a']

# Allowed data file extensions for bulk upload
ALLOWED_CSVFILE_EXTENSIONS = ['csv', 'xls', 'xlsx']

# Maximum number of times changing the username is allowed
USERNAME_CHANGE_MAX_TIMES = 3

# Anti-spam restrictions for posting comments, messages and in forums
# Time since last post (in seconds) and maximum number of posts per day
LAST_FORUM_POST_MINIMUM_TIME = 60 * 5
BASE_MAX_POSTS_PER_DAY = 5

# Random Sound of the day settings
# Don't choose a sound by a user whose sound has been chosen in the last ~1 month
NUMBER_OF_DAYS_FOR_USER_RANDOM_SOUNDS = 30
NUMBER_OF_RANDOM_SOUNDS_IN_ADVANCE = 5

# Number of ratings of a sound to start showing average
MIN_NUMBER_RATINGS = 3

# Buffer size for CRC computation
CRC_BUFFER_SIZE = 4096

# Maximum combined file size for uploading files. This is set in nginx configuration
UPLOAD_MAX_FILE_SIZE_COMBINED = 1024 * 1024 * 1024  # 1 GB

# Minimum number of sounds that a user has to upload before enabling bulk upload feature for that user
BULK_UPLOAD_MIN_SOUNDS = 40

# Turn this option on to log every time a user downloads a pack or sound
LOG_DOWNLOADS = False

# Followers notifications
MAX_EMAILS_PER_COMMAND_RUN = 1000
NOTIFICATION_TIMEDELTA_PERIOD = datetime.timedelta(days=7)


# -------------------------------------------------------------------------------
# Freesound data paths and urls

# Base data path. Note that further data subdirectories are defined after the local_settings import
DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../freesound-data/'))

# Base data URL. Note that further data sub-urls are defined after the local_settings import
# You can overwrite this to point to production data ("https://freesound.org/data/")
DATA_URL = "/data/"

SENDFILE_SECRET_URL = "/secret/"
SOUNDS_SENDFILE_URL = SENDFILE_SECRET_URL + "sounds/"
PACKS_SENDFILE_URL = SENDFILE_SECRET_URL + "packs/"

# Locations where sounds, previews and other "static" content will be mirrored (if specified)
# If locations do not exist, they will be created
MIRROR_SOUNDS = None  # list of locations to mirror contents of SOUNDS_PATH, set to None to turn off
MIRROR_PREVIEWS = None  # list of locations to mirror contents of SOUNDS_PATH, set to None to turn off
MIRROR_DISPLAYS = None  # list of locations to mirror contents of SOUNDS_PATH, set to None to turn off
MIRROR_ANALYSIS = None  # list of locations to mirror contents of SOUNDS_PATH, set to None to turn off
MIRROR_AVATARS = None  # list of locations to mirror contents of AVATARS_PATH, set to None to turn off
MIRROR_UPLOADS = None  # list of locations to mirror contents of MIRROR_UPLOADS, set to None to turn off
LOG_START_AND_END_COPYING_FILES = True


# -------------------------------------------------------------------------------
# Donations

DONATION_AMOUNT_REQUEST_PARAM = 'dda'

# Stripe
STRIPE_PUBLIC_KEY = ''
STRIPE_PRIVATE_KEY = ''
STRIPE_WEBHOOK_SECRET = ''

# Paypal
PAYPAL_EMAIL = "fs@freesound.org"
PAYPAL_VALIDATION_URL = ''
PAYPAL_PAYMENTS_API_URL = ''
PAYPAL_PASSWORD = ''
PAYPAL_USERNAME = ''
PAYPAL_SIGNATURE = ''


# -------------------------------------------------------------------------------
# AudioCommons analysis settings

AUDIOCOMMONS_EXTRACTOR_NAME = 'AudioCommonsV3'  # This will be used for indexing sounds and returning analysis output
AUDIOCOMMONS_DESCRIPTOR_PREFIX = 'ac_'
AUDIOCOMMONS_INCLUDED_DESCRIPTOR_NAMES_TYPES = \
    [('loudness', float),
     ('dynamic_range', float),
     ('temporal_centroid', float),
     ('log_attack_time', float),
     ('single_event', bool),
     ('tonality', str),
     ('tonality_confidence', float),
     ('loop', bool),
     ('tempo', int),
     ('tempo_confidence', float),
     ('note_midi', int),
     ('note_name', str),
     ('note_frequency', float),
     ('note_confidence', float),
     ('brightness', float),
     ('depth', float),
     ('hardness', float),
     ('roughness', float),
     ('boominess', float),
     ('warmth', float),
     ('sharpness', float),
     ('reverb', bool)]  # Used when running load_audiocommons_analysis_data and when parsing filters

# Map of suffixes used for each type of dynamic fields defined in our Solr schema
# The dynamic field names we define in Solr schema are '*_b' (for bool), '*_d' (for float), '*_i' (for integer)
# and '*_s' (for string)
SOLR_DYNAMIC_FIELDS_SUFFIX_MAP = {
    float: '_d',
    int: '_i',
    bool: '_b',
    str: '_s',
    unicode: '_s',
}


# -------------------------------------------------------------------------------
# SOLR and search settings
SOLR_URL = "http://search:8080/fs2/"
SOLR_FORUM_URL = "http://search:8080/forum/"

ENABLE_QUERY_SUGGESTIONS = False  # Only for BW
DEFAULT_SEARCH_WEIGHTS = {
    'id': 4,
    'tag': 4,
    'description': 3,
    'username': 1,
    'pack_tokenized': 2,
    'original_filename': 2
}


# -------------------------------------------------------------------------------
# Similarity client settings
SIMILARITY_ADDRESS = 'similarity'
SIMILARITY_PORT = 8008
SIMILARITY_INDEXING_SERVER_PORT = 8009

# -------------------------------------------------------------------------------
# Tag recommendation client settings
TAGRECOMMENDATION_ADDRESS = 'tagrecommendation'
TAGRECOMMENDATION_PORT = 8010
TAGRECOMMENDATION_CACHE_TIME = 60 * 60 * 24 * 7

# -------------------------------------------------------------------------------
# Sentry settings
SENTRY_DSN = None


# -------------------------------------------------------------------------------
# Google analytics settings
GOOGLE_ANALYTICS_KEY = ''


# -------------------------------------------------------------------------------
# Zendesk settings
USE_ZENDESK_FOR_SUPPORT_REQUESTS = False
ZENDESK_EMAIL = ''
ZENDESK_TOKEN = ''

# -------------------------------------------------------------------------------
# Graylog settings

GRAYLOG_API_STREAM_ID = '530f2ec5e4b0f124869546d0'
GRAYLOG_SEARCH_STREAM_ID = '531051bee4b0f1248696785a'
GRAYLOG_DOMAIN = ''
GRAYLOG_USERNAME = ''
GRAYLOG_PASSWORD = ''

# -------------------------------------------------------------------------------
# Mapbox

MAPBOX_ACCESS_TOKEN = ''


# -------------------------------------------------------------------------------
# Recaptcha settings

RECAPTCHA_PRIVATE_KEY = ''
RECAPTCHA_PUBLIC_KEY = ''


# -------------------------------------------------------------------------------
# Mapbox

AKISMET_KEY = ''

# -------------------------------------------------------------------------------
# Processing and analysis settings

GEARMAN_JOB_SERVERS = ["gearmand:4730"]

STEREOFY_PATH = '/usr/local/bin/stereofy'

# Min free disk space percentage for worker (worker will raise exception if not enough free disk space is available)
WORKER_MIN_FREE_DISK_SPACE_PERCENTAGE = 0.05

# General timeout for processing/analysis workers (in seconds)
WORKER_TIMEOUT = 60 * 60

ESSENTIA_EXECUTABLE = '/usr/local/bin/essentia_streaming_extractor_freesound'
ESSENTIA_STATS_OUT_FORMAT = 'yaml'
ESSENTIA_FRAMES_OUT_FORMAT = 'yaml'

# Used to configure output formats in newer FreesoundExtractor versions
ESSENTIA_PROFILE_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils/audioprocessing/essentia_profile.yaml'))

# Files above this filesize after converting to 16bit mono PCM won't be analyzed (in bytes, ~5MB per minute).
MAX_FILESIZE_FOR_ANALYSIS = 5 * 1024 * 1024 * 25


# -------------------------------------------------------------------------------
# API settings

ALLOW_WRITE_WHEN_SESSION_BASED_AUTHENTICATION = False
APIV2_RESOURCES_REQUIRING_HTTPS = ['apiv2-sound-download',
                                   'apiv2-user-sound-edit',
                                   'apiv2-user-create-bookmark',
                                   'apiv2-user-create-rating',
                                   'apiv2-user-create-comment',
                                   'apiv2-uploads-upload',
                                   'apiv2-uploads-pending',
                                   'apiv2-uploads-describe',
                                   'apiv2-pack-download','apiv2-me',
                                   'apiv2-logout-oauth2-user',
                                   'oauth2:capture',
                                   'oauth2:authorize',
                                   'oauth2:redirect',
                                   'oauth2:access_token',
                                   'api-login']

APIV2 = {
    'PAGE_SIZE': 15,
    'PAGE_SIZE_QUERY_PARAM': 'page_size',
    'MAX_PAGE_SIZE': 150,
}

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'apiv2.pagination.CustomPagination',
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
        'rest_framework_yaml.renderers.YAMLRenderer',
        'rest_framework_jsonp.renderers.JSONPRenderer',
        'rest_framework_xml.renderers.XMLRenderer',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'apiv2.throttling.ClientBasedThrottlingBurst',
        'apiv2.throttling.ClientBasedThrottlingSustained',
        'apiv2.throttling.IpBasedThrottling',
    ),
    'VIEW_DESCRIPTION_FUNCTION': 'apiv2.apiv2_utils.get_view_description',
}

API_DOWNLOAD_TOKEN_LIFETIME = 60*60  # 1 hour

OAUTH2_PROVIDER = {
    'ACCESS_TOKEN_EXPIRE_SECONDS': 60*60*24,
    'CLIENT_SECRET_GENERATOR_LENGTH': 40,
    'AUTHORIZATION_CODE_EXPIRE_SECONDS': 10*60,
    'OAUTH2_VALIDATOR_CLASS': 'apiv2.oauth2_validators.OAuth2Validator',
    'REQUEST_APPROVAL_PROMPT': 'auto',
    'CLIENT_ID_GENERATOR_CLASS': 'apiv2.apiv2_utils.FsClientIdGenerator'
}
OAUTH2_PROVIDER_APPLICATION_MODEL = 'oauth2_provider.Application'

# APIv2 throttling limits
# Define API usage limit rates per defined throttling levels
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


# -------------------------------------------------------------------------------
# Frontend handling

FRONTEND_CHOOSER_REQ_PARAM_NAME = 'fend'
FRONTEND_SESSION_PARAM_NAME = 'frontend'
FRONTEND_NIGHTINGALE = 'ng'  # https://freesound.org/people/reinsamba/sounds/14854/
FRONTEND_BEASTWHOOSH = 'bw'  # https://freesound.org/people/martian/sounds/403973/
FRONTEND_DEFAULT = FRONTEND_NIGHTINGALE
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(os.path.dirname(__file__), '../templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'freesound.context_processor.context_extra',
            ],
        },
        'NAME': FRONTEND_NIGHTINGALE,
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(os.path.dirname(__file__), '../templates_bw'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'freesound.context_processor.context_extra',
            ],
        },
        'NAME': FRONTEND_BEASTWHOOSH,
    },

]

# We use the last restart date as a timestamp of the last time freesound web was restarted (lat time
# settings were loaded). We add this variable to the context processor and use it in base.html as a
# parameter for the url of all.css and freesound.js files, so me make sure client browsers update these
# files when we do a deploy (the url changes)
LAST_RESTART_DATE = datetime.datetime.now().strftime("%d%m")


# -------------------------------------------------------------------------------
# Import local settings
# Important: place settings which depend on other settings potentially modified in local_settings.py BELOW the import
from local_settings import *


# -------------------------------------------------------------------------------
# Sentry

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        send_default_pii=True
    )


# -------------------------------------------------------------------------------
# Extra Freesound settings

# Paths (depend on DATA_PATH potentially re-defined in local_settings.py)
# If new paths are added here, remember to add a line for them at general.apps.GeneralConfig. This will ensure
# directories are created if not existing
AVATARS_PATH = os.path.join(DATA_PATH, "avatars/")
PREVIEWS_PATH = os.path.join(DATA_PATH, "previews/")
DISPLAYS_PATH = os.path.join(DATA_PATH, "displays/")
SOUNDS_PATH = os.path.join(DATA_PATH, "sounds/")
PACKS_PATH = os.path.join(DATA_PATH, "packs/")
UPLOADS_PATH = os.path.join(DATA_PATH, "uploads/")
CSV_PATH = os.path.join(DATA_PATH, "csv/")
ANALYSIS_PATH = os.path.join(DATA_PATH, "analysis/")
FILE_UPLOAD_TEMP_DIR = os.path.join(DATA_PATH, "tmp_uploads/")
PROCESSING_TEMP_DIR = os.path.join(DATA_PATH, "tmp_processing/")

# URLs (depend on DATA_URL potentially re-defined in local_settings.py)
AVATARS_URL = DATA_URL + "avatars/"
PREVIEWS_URL = DATA_URL + "previews/"
DISPLAYS_URL = DATA_URL + "displays/"
ANALYSIS_URL = DATA_URL + "analysis/"


# -------------------------------------------------------------------------------
# Settings depending on DEBUG config

# In a typical development setup original files won't be available in the filesystem, but preview files
# might be available as these take much less space. The flag below will configure Freesound to use these
# preview files (instead of the originals) for processing and downloading when the originals are not available.
USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING = DEBUG

if DEBUG and DISPLAY_DEBUG_TOOLBAR:
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INSTALLED_APPS += ['debug_toolbar']

    DEBUG_TOOLBAR_PANELS = [
        'debug_toolbar.panels.versions.VersionsPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
        'debug_toolbar.panels.templates.TemplatesPanel',
        'debug_toolbar.panels.cache.CachePanel',
        'debug_toolbar.panels.signals.SignalsPanel',
        'debug_toolbar.panels.logging.LoggingPanel',
        'debug_toolbar.panels.redirects.RedirectsPanel',
    ]

    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
        # This normally checks the running host with the request url, but this doesn't
        # work in docker. Unconditionally show the toolbar when DEBUG is True
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG
    }

# -------------------------------------------------------------------------------
# Import logging settings
from logger import LOGGING
