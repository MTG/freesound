# -*- coding: utf-8 -*-

import datetime
import logging.config
import os
import re

import dj_database_url
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# -------------------------------------------------------------------------------
# Miscellaneous Django settings

DEBUG = False
DISPLAY_DEBUG_TOOLBAR = False

DEBUGGER_HOST = "0.0.0.0"
DEBUGGER_PORT = 3000  # This port should match the one in docker compose

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '___this_is_a_secret_key_that_should_not_be_used___')

default_url = 'postgres://postgres@db/postgres'
DATABASES = {'default': dj_database_url.config('DJANGO_DATABASE_URL', default=default_url)}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'silk.middleware.SilkyMiddleware',
    'admin_reorder.middleware.ModelAdminReorder',
    'ratelimit.middleware.RatelimitMiddleware',
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
    'clustering',
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
    'admin_reorder',
]

# Specify custom ordering of models in Django Admin index
ADMIN_REORDER = (

    {'app': 'accounts', 'models': (
        'auth.User',
        'accounts.Profile',
        'accounts.DeletedUser',
        'accounts.UserDeletionRequest',
        'accounts.UserFlag',
        'accounts.OldUsername',
        'accounts.EmailBounce',
        'auth.Groups',
        'fsmessages.Message'
    )},
    {'app': 'sounds', 'models': (
        'sounds.Sound',
        {'model': 'sounds.SoundAnalysis', 'label': 'Sound analyses'},
        'sounds.Pack',
        'sounds.DeletedSound',
        'sounds.License',
        {'model': 'sounds.Flag', 'label': 'Sound flags'},
        'sounds.BulkUploadProgress',
        {'model': 'sounds.SoundOfTheDay', 'label': 'Sound of the day'}
    )},
    {'app': 'apiv2', 'label': 'API', 'models': (
        {'model': 'apiv2.ApiV2Client', 'label': 'API V2 Application'},
        'oauth2_provider.AccessToken',
        'oauth2_provider.RefreshToken',
        'oauth2_provider.Grant',
    )},
    'forum',
    {'app': 'donations', 'models': (
        'donations.Donation',
        'donations.DonationsEmailSettings',
        'donations.DonationsModalSettings',
    )},
    'sites',
)

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

# Redis and caches
# NOTE: some of these settings need to be re-defined in local_settings.py (eg to build cache urls)
# We should optimize that so settings do not need to be re-defined
REDIS_HOST = 'redis'
REDIS_PORT = 6379
API_MONITORING_REDIS_STORE_ID = 0
CACHE_REDIS_STORE_ID = 1
AUDIO_FEATURES_REDIS_STORE_ID = 2
CELERY_BROKER_REDIS_STORE_ID = 3

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'api_monitoring': {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://{}:{}/{}".format(REDIS_HOST, REDIS_PORT, API_MONITORING_REDIS_STORE_ID),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    },
    'clustering': {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://{}:{}/{}".format(REDIS_HOST, REDIS_PORT, CACHE_REDIS_STORE_ID),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
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
DEFAULT_FROM_EMAIL = 'Freesound NoReply <noreply@freesound.org>'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25

# AWS credentials for sending email (SES)
AWS_REGION = ''
AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''

# AWS credentials for accessing bounces queue (SQS)
AWS_SQS_REGION = ''
AWS_SQS_ACCESS_KEY_ID = ''
AWS_SQS_SECRET_ACCESS_KEY = ''
AWS_SQS_QUEUE_URL = ''
AWS_SQS_MESSAGES_PER_CALL = 1  # between 1 and 10, see accounts management command `process_email_bounces` for more

# Email stats retrieval parameters (see utils.aws.report_ses_stats for more details)
AWS_SES_BOUNCE_RATE_SAMPLE_SIZE = 10500  # should be ~ 10000-11000
AWS_SES_SHORT_BOUNCE_RATE_DATAPOINTS = 4  # cron period (1hr) / AWS stats period (15min)

# If ALLOWED emails is not empty, only emails going to these destinations will be actually sent
ALLOWED_EMAILS = []

# Email subjects
EMAIL_SUBJECT_PREFIX = u'[freesound]'
EMAIL_SUBJECT_ACTIVATION_LINK = u'Your activation link'
EMAIL_SUBJECT_USERNAME_REMINDER = u'Username reminder'
EMAIL_SUBJECT_EMAIL_CHANGED = u'Email address changed'
EMAIL_SUBJECT_USER_SPAM_REPORT = u'Spam/offensive report for user'
EMAIL_SUBJECT_DONATION_THANK_YOU = u'Thanks for your donation!'
EMAIL_SUBJECT_DONATION_REMINDER = u'Thanks for contributing to Freesound'
EMAIL_SUBJECT_DONATION_REQUEST = u'Have you considered making a donation?'
EMAIL_SUBJECT_STREAM_EMAILS = u'New sounds from users and tags you are following'
EMAIL_SUBJECT_TOPIC_REPLY = u'Topic reply notification'
EMAIL_SUBJECT_PRIVATE_MESSAGE = u'You have a private message'
EMAIL_SUBJECT_SOUND_ADDED_AS_REMIX = u'Sound added as remix source'
EMAIL_SUBJECT_RANDOM_SOUND_OF_THE_SAY_CHOOSEN = u'One of your sounds has been chosen as random sound of the day!'
EMAIL_SUBJECT_NEW_COMMENT = u'You have a new comment'
EMAIL_SUBJECT_SOUND_FLAG = u'Sound flag'
EMAIL_SUBJECT_SUPPORT_EMAIL = u'[support]'
EMAIL_SUBJECT_MODERATION_HANDLED = u'A Freesound moderator handled your upload'

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
FORUM_THREADS_PER_PAGE_BW = 15
SOUND_COMMENTS_PER_PAGE = 5
SOUNDS_PER_PAGE = 15
PACKS_PER_PAGE = 15
REMIXES_PER_PAGE = 10
MAX_TICKETS_IN_MODERATION_ASSIGNED_PAGE = 100
MAX_TICKETS_IN_MODERATION_ASSIGNED_PAGE_SELECTED_COLUMN = 20
SOUNDS_PER_DESCRIBE_ROUND = 10
SOUNDS_PENDING_MODERATION_PER_PAGE = 8
MAX_UNMODERATED_SOUNDS_IN_HOME_PAGE = 5
DONATIONS_PER_PAGE = 40
FOLLOW_ITEMS_PER_PAGE = 5  # BW only

BW_CHARTS_ACTIVE_USERS_WEIGHTS = {'upload': 1, 'post': 0.8, 'comment': 0.05}

# User flagging notification thresholds
USERFLAG_THRESHOLD_FOR_NOTIFICATION = 3
USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING = 6

ALLOWED_AUDIOFILE_EXTENSIONS = ['wav', 'aiff', 'aif', 'ogg', 'flac', 'mp3', 'm4a']
LOSSY_FILE_EXTENSIONS = [ 'ogg', 'mp3', 'm4a']
COMMON_BITRATES = [32, 64, 96, 128, 160, 192, 224, 256, 320]

# Allowed data file extensions for bulk upload
ALLOWED_CSVFILE_EXTENSIONS = ['csv', 'xls', 'xlsx']

# Maximum number of times changing the username is allowed
USERNAME_CHANGE_MAX_TIMES = 3

# Number of hours we give to the async delete workers for deleting a user
# before considering that deletion failed and therefore reporting that there i
# one user that should have been deleted and was not
CHECK_ASYNC_DELETED_USERS_HOURS_BACK = 1

# Anti-spam restrictions for posting comments, messages and in forums
# Time since last post (in seconds) and maximum number of posts per day
LAST_FORUM_POST_MINIMUM_TIME = 60 * 5
BASE_MAX_POSTS_PER_DAY = 5
SPAM_BLACKLIST = []

# Random Sound of the day settings
# Don't choose a sound by a user whose sound has been chosen in the last ~1 month
NUMBER_OF_DAYS_FOR_USER_RANDOM_SOUNDS = 30
NUMBER_OF_RANDOM_SOUNDS_IN_ADVANCE = 5
RANDOM_SOUND_OF_THE_DAY_CACHE_KEY = "random_sound"

#Geotags  stuff
# Cache key for storing "all geotags" bytearray
ALL_GEOTAGS_BYTEARRAY_CACHE_KEY = "geotags_bytearray"
USE_TEXTUAL_LOCATION_NAMES_IN_BW = True

# Avatar background colors (only BW)
from utils.audioprocessing.processing import interpolate_colors
from utils.audioprocessing.color_schemes import BEASTWHOOSH_COLOR_SCHEME, COLOR_SCHEMES
AVATAR_BG_COLORS = interpolate_colors(COLOR_SCHEMES[BEASTWHOOSH_COLOR_SCHEME]['wave_colors'][1:], num_colors=10)

# Number of ratings of a sound to start showing average
MIN_NUMBER_RATINGS = 3

# Buffer size for CRC computation
CRC_BUFFER_SIZE = 4096

# Maximum combined file size for uploading files. This is set in nginx configuration
UPLOAD_MAX_FILE_SIZE_COMBINED = 1024 * 1024 * 1024  # 1 GB
MOVE_TMP_UPLOAD_FILES_INSTEAD_OF_COPYTING = True

# Minimum number of sounds that a user has to upload before enabling bulk upload feature for that user
BULK_UPLOAD_MIN_SOUNDS = 40

# Turn this option on to log every time a user downloads a pack or sound
LOG_DOWNLOADS = False

# Followers notifications
MAX_EMAILS_PER_COMMAND_RUN = 5000
NOTIFICATION_TIMEDELTA_PERIOD = datetime.timedelta(days=7)

# Some BW settings
ENABLE_QUERY_SUGGESTIONS = False
ENABLE_POPULAR_SEARCHES_IN_FRONTPAGE = False


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
STRIPE_PUBLIC_KEY = 'pk_test_4w86cbKHcPs2G2kDqNdKd5u2'
STRIPE_PRIVATE_KEY = 'sk_test_D4u7pcSnUSXtY4GAwDMmSFVZ'
STRIPE_WEBHOOK_SECRET = ''

# Paypal
PAYPAL_EMAIL = "fs@freesound.org"
PAYPAL_VALIDATION_URL = ''
PAYPAL_PAYMENTS_API_URL = ''
PAYPAL_PASSWORD = ''
PAYPAL_USERNAME = ''
PAYPAL_SIGNATURE = ''


# -------------------------------------------------------------------------------
# New Analysis options
ORCHESTRATE_ANALYSIS_MAX_JOBS_PER_QUEUE_DEFAULT = 500
ORCHESTRATE_ANALYSIS_MAX_NUM_ANALYSIS_ATTEMPTS = 3
ORCHESTRATE_ANALYSIS_MAX_TIME_IN_QUEUED_STATUS = 24 * 2 # in hours
ORCHESTRATE_ANALYSIS_MAX_TIME_CONVERTED_FILES_IN_DISK = 24 * 7 # in hours

AUDIOCOMMONS_ANALYZER_NAME = 'ac-extractor_v3'
FREESOUND_ESSENTIA_EXTRACTOR_NAME = 'fs-essentia-extractor_legacy'
AUDIOSET_YAMNET_ANALYZER_NAME = 'audioset-yamnet_v1'

ANALYZERS_CONFIGURATION = {
    AUDIOCOMMONS_ANALYZER_NAME: {
        'descriptors_map': [
            ('loudness', 'ac_loudness', float),
            ('dynamic_range', 'ac_dynamic_range', float),
            ('temporal_centroid', 'ac_temporal_centroid', float),
            ('log_attack_time', 'ac_log_attack_time', float),
            ('single_event', 'ac_single_event', bool),
            ('tonality', 'ac_tonality', str),
            ('tonality_confidence', 'ac_tonality_confidence', float),
            ('loop', 'ac_loop', bool),
            ('tempo', 'ac_tempo', int),
            ('tempo_confidence', 'ac_tempo_confidence', float),
            ('note_midi', 'ac_note_midi', int),
            ('note_name', 'ac_note_name', str),
            ('note_frequency', 'ac_note_frequency', float),
            ('note_confidence', 'ac_note_confidence', float),
            ('brightness', 'ac_brightness', float),
            ('depth', 'ac_depth', float),
            ('hardness', 'ac_hardness', float),
            ('roughness', 'ac_roughness', float),
            ('boominess', 'ac_boominess', float),
            ('warmth', 'ac_warmth', float),
            ('sharpness', 'ac_sharpness', float),
            ('reverb', 'ac_reverb', bool)
        ]
    },
    FREESOUND_ESSENTIA_EXTRACTOR_NAME: {},
    AUDIOSET_YAMNET_ANALYZER_NAME: {
        'descriptors_map': [
            ('classes', 'yamnet_class', list)
        ]
    },
}

# -------------------------------------------------------------------------------
# Search engine

# Define the names of some of the indexed sound fields which are to be used later
SEARCH_SOUNDS_FIELD_ID = 'sound_id'
SEARCH_SOUNDS_FIELD_NAME = 'name'
SEARCH_SOUNDS_FIELD_TAGS = 'tags'
SEARCH_SOUNDS_FIELD_DESCRIPTION = 'description'
SEARCH_SOUNDS_FIELD_USER_NAME = 'username'
SEARCH_SOUNDS_FIELD_PACK_NAME = 'packname'
SEARCH_SOUNDS_FIELD_PACK_GROUPING = 'pack_grouping'
SEARCH_SOUNDS_FIELD_SAMPLERATE = 'samplerate'
SEARCH_SOUNDS_FIELD_BITRATE = 'bitrate'
SEARCH_SOUNDS_FIELD_BITDEPTH = 'bitdepth'
SEARCH_SOUNDS_FIELD_TYPE = 'type'
SEARCH_SOUNDS_FIELD_CHANNELS = 'channels'
SEARCH_SOUNDS_FIELD_LICENSE_NAME = 'license'

# Default weights for fields to match
SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS = {
    SEARCH_SOUNDS_FIELD_ID: 4,
    SEARCH_SOUNDS_FIELD_TAGS: 4,
    SEARCH_SOUNDS_FIELD_DESCRIPTION: 3,
    SEARCH_SOUNDS_FIELD_USER_NAME: 1,
    SEARCH_SOUNDS_FIELD_PACK_NAME: 2,
    SEARCH_SOUNDS_FIELD_NAME: 2
}


SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC = "Automatic by relevance"
SEARCH_SOUNDS_SORT_OPTION_DURATION_LONG_FIRST = "Duration (long first)"
SEARCH_SOUNDS_SORT_OPTION_DURATION_SHORT_FIRST = "Duration (short first)"
SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST = "Date added (newest first)"
SEARCH_SOUNDS_SORT_OPTION_DATE_OLD_FIRST = "Date added (oldest first)"
SEARCH_SOUNDS_SORT_OPTION_DOWNLOADS_MOST_FIRST = "Downloads (most first)"
SEARCH_SOUNDS_SORT_OPTION_DOWNLOADS_LEAST_FIRST = "Downloads (least first)"
SEARCH_SOUNDS_SORT_OPTION_RATING_HIGHEST_FIRST = "Rating (highest first)"
SEARCH_SOUNDS_SORT_OPTION_RATING_LOWEST_FIRST = "Rating (lowest first)"

SEARCH_SOUNDS_SORT_OPTIONS_WEB = [
    SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC,
    SEARCH_SOUNDS_SORT_OPTION_DURATION_LONG_FIRST,
    SEARCH_SOUNDS_SORT_OPTION_DURATION_SHORT_FIRST,
    SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST,
    SEARCH_SOUNDS_SORT_OPTION_DATE_OLD_FIRST,
    SEARCH_SOUNDS_SORT_OPTION_DOWNLOADS_MOST_FIRST,
    SEARCH_SOUNDS_SORT_OPTION_DOWNLOADS_LEAST_FIRST,
    SEARCH_SOUNDS_SORT_OPTION_RATING_HIGHEST_FIRST,
    SEARCH_SOUNDS_SORT_OPTION_RATING_LOWEST_FIRST,
]
SEARCH_SOUNDS_SORT_DEFAULT = "Automatic by relevance"


SEARCH_SOUNDS_DEFAULT_FACETS = {
    SEARCH_SOUNDS_FIELD_SAMPLERATE: {},
    SEARCH_SOUNDS_FIELD_PACK_GROUPING: {'limit': 10},
    SEARCH_SOUNDS_FIELD_USER_NAME: {'limit': 30},
    SEARCH_SOUNDS_FIELD_TAGS: {'limit': 30},
    SEARCH_SOUNDS_FIELD_BITRATE: {},
    SEARCH_SOUNDS_FIELD_BITDEPTH: {},
    SEARCH_SOUNDS_FIELD_TYPE: {'limit': 6},  # Set after the number of choices in sounds.models.Sound.SOUND_TYPE_CHOICES
    SEARCH_SOUNDS_FIELD_CHANNELS: {},
    SEARCH_SOUNDS_FIELD_LICENSE_NAME: {'limit': 10},
}

SEARCH_ENGINE_BACKEND_CLASS = 'utils.search.backends.solr451custom.Solr451CustomSearchEngine'
SOLR_SOUNDS_URL = "http://search:8080/fs2/"
SOLR_FORUM_URL = "http://search:8080/forum/"


# -------------------------------------------------------------------------------
# Similarity client settings
SIMILARITY_ADDRESS = 'similarity'
SIMILARITY_PORT = 8008
SIMILARITY_INDEXING_SERVER_PORT = 8009
SIMILARITY_TIMEOUT = 10

# -------------------------------------------------------------------------------
# Tag recommendation client settings
TAGRECOMMENDATION_ADDRESS = 'tagrecommendation'
TAGRECOMMENDATION_PORT = 8010
TAGRECOMMENDATION_CACHE_TIME = 60 * 60 * 24 * 7
TAGRECOMMENDATION_TIMEOUT = 10

# -------------------------------------------------------------------------------
# Sentry settings
SENTRY_DSN = None

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
MAPBOX_USE_STATIC_MAPS_BEFORE_LOADING = True


# -------------------------------------------------------------------------------
# Recaptcha settings

RECAPTCHA_PRIVATE_KEY = ''
RECAPTCHA_PUBLIC_KEY = ''


# -------------------------------------------------------------------------------
# Akismet

AKISMET_KEY = ''

# -------------------------------------------------------------------------------
# Processing and analysis settings

STEREOFY_PATH = '/usr/local/bin/stereofy'

# Min free disk space percentage for worker (worker will raise exception if not enough free disk space is available)
WORKER_MIN_FREE_DISK_SPACE_PERCENTAGE = 0.05

# General timeout for processing/analysis workers (in seconds)
WORKER_TIMEOUT = 60 * 60

ESSENTIA_EXECUTABLE = '/usr/local/bin/essentia_streaming_extractor_freesound'
ESSENTIA_STATS_OUT_FORMAT = 'yaml'
ESSENTIA_FRAMES_OUT_FORMAT = 'json'

# Used to configure output formats in newer FreesoundExtractor versions
ESSENTIA_PROFILE_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils/audioprocessing/essentia_profile.yaml'))

# Files above this filesize after converting to 16bit mono PCM won't be analyzed (in bytes, ~5MB per minute).
MAX_FILESIZE_FOR_ANALYSIS = 5 * 1024 * 1024 * 25

# -------------------------------------------------------------------------------
# Search results clustering
# NOTE: celery configuration is set after the local settings import

# Environment variables
# '1' indicates that a process is running as a celery worker.
# We get it from environment variable to avoid the need of a specific settings file for celery workers.
# We enable the imports of clustering dependencies only in celery workers.
IS_CELERY_WORKER = os.getenv('ENV_CELERY_WORKER', None) == "1"

# Determines whether to use or not the clustering feature.
# Set to False by default (to be overwritten in local_settings.py)
# When activated, Enables to do js calls & html clustering facets rendering
ENABLE_SEARCH_RESULTS_CLUSTERING = False

# -------------------------------------------------------------------------------
# Rate limiting

RATELIMIT_VIEW = 'accounts.views.ratelimited_error'
RATELIMIT_SEARCH_GROUP = 'search'
RATELIMIT_SIMILARITY_GROUP = 'similarity'
RATELIMIT_DEFAULT_GROUP_RATELIMIT = '2/s'
RATELIMITS = {
    RATELIMIT_SEARCH_GROUP: '2/s',
    RATELIMIT_SIMILARITY_GROUP: '2/s'
}
BLOCKED_IPS = []
CACHED_BLOCKED_IPS_KEY = 'cached_blocked_ips'
CACHED_BLOCKED_IPS_TIME = 60 * 5  # 5 minutes

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
# Analytics
PLAUSIBLE_AGGREGATE_PAGEVIEWS = True
PLAUSIBLE_SEPARATE_FRONTENDS = True

# -------------------------------------------------------------------------------
# Rabbit MQ 
RABBITMQ_USER = "guest"
RABBITMQ_PASS = "guest"
RABBITMQ_HOST = 'rabbitmq'
RABBITMQ_PORT = '5672'
RABBITMQ_API_PORT = '15672'


# -------------------------------------------------------------------------------
# Import local settings
# Important: place settings which depend on other settings potentially modified in local_settings.py BELOW the import
from local_settings import *


# -------------------------------------------------------------------------------
# Celery
CELERY_BROKER_URL = 'amqp://{}:{}@{}:{}//'.format(RABBITMQ_USER, RABBITMQ_PASS, RABBITMQ_HOST, RABBITMQ_PORT)
CELERY_RESULT_BACKEND = 'redis://{}:{}/{}'.format(REDIS_HOST, REDIS_PORT, CELERY_BROKER_REDIS_STORE_ID)
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ASYNC_TASKS_QUEUE_NAME = 'async_tasks_queue'
CELERY_SOUND_PROCESSING_QUEUE_NAME = 'sound_processing_queue'
CELERY_SOUND_ANALYSIS_OLD_QUEUE_NAME = 'sound_analysis_old_queue'


# -------------------------------------------------------------------------------
# Sentry

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        default_integrations=False,
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
ANALYSIS_NEW_PATH = os.path.join(DATA_PATH, "analysis_new/")
FILE_UPLOAD_TEMP_DIR = os.path.join(DATA_PATH, "tmp_uploads/")
PROCESSING_TEMP_DIR = os.path.join(DATA_PATH, "tmp_processing/")

# URLs (depend on DATA_URL potentially re-defined in local_settings.py)
AVATARS_URL = DATA_URL + "avatars/"
PREVIEWS_URL = DATA_URL + "previews/"
DISPLAYS_URL = DATA_URL + "displays/"
ANALYSIS_URL = DATA_URL + "analysis/"

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
