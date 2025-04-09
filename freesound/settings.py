import datetime
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

DEFAULT_AUTO_FIELD='django.db.models.AutoField'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'silk.middleware.SilkyMiddleware',
    'django_ratelimit.middleware.RatelimitMiddleware',
    'freesound.middleware.TosAcceptanceHandler',
    'freesound.middleware.BulkChangeLicenseHandler',
    'freesound.middleware.UpdateEmailHandler',
    'corsheaders.middleware.CorsMiddleware',
]

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django.contrib.admin',
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
    'utils',
    'donations',
    'monitor',
    'django_object_actions',
    'silk',
    'django_recaptcha',
    'adminsortable',
]

# Silk is the Request/SQL logging platform. We install it but leave it disabled
# It can be activated in local_settings by changing INTERCEPT_FUNC
SILKY_AUTHENTICATION = True  # User must login
SILKY_AUTHORISATION = True  # User must have permissions
SILKY_PERMISSIONS = lambda user: user.is_superuser
SILKY_INTERCEPT_FUNC = lambda request: False

CORS_ALLOW_ALL_ORIGINS = True

AUTHENTICATION_BACKENDS = ('accounts.modelbackend.CustomModelBackend',)

# This was the default serializer in django 1.6. Now we keep using it because
# we saw some errors when running tests, in the future we should change to the
# new one.
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

TIME_ZONE = 'Europe/Brussels'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_X_FORWARDED_HOST = True

USE_TZ = True

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# Redis and caches
# NOTE: some of these settings need to be re-defined in local_settings.py (eg to build cache urls)
# We should optimize that so settings do not need to be re-defined
REDIS_HOST = 'redis'
REDIS_PORT = 6379
API_MONITORING_REDIS_STORE_ID = 0
CLUSTERING_CACHE_REDIS_STORE_ID = 1
AUDIO_FEATURES_REDIS_STORE_ID = 2
CELERY_BROKER_REDIS_STORE_ID = 3
CDN_MAP_STORE_ID = 5

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'api_monitoring': {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/{API_MONITORING_REDIS_STORE_ID}",
    },
    'cdn_map': {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/{CDN_MAP_STORE_ID}",
    },
    'clustering': {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/{CLUSTERING_CACHE_REDIS_STORE_ID}",
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

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
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
EMAIL_SUBJECT_PREFIX = '[freesound]'
EMAIL_SUBJECT_ACTIVATION_LINK = 'Your activation link'
EMAIL_SUBJECT_USERNAME_REMINDER = 'Username reminder'
EMAIL_SUBJECT_EMAIL_CHANGED = 'Email address changed'
EMAIL_SUBJECT_USER_SPAM_REPORT = 'Spam/offensive report for user'
EMAIL_SUBJECT_DONATION_THANK_YOU = 'Thanks for your donation!'
EMAIL_SUBJECT_DONATION_REMINDER = 'Thanks for contributing to Freesound'
EMAIL_SUBJECT_DONATION_REQUEST = 'Have you considered making a donation?'
EMAIL_SUBJECT_STREAM_EMAILS = 'New sounds from users and tags you are following'
EMAIL_SUBJECT_TOPIC_REPLY = 'Topic reply notification'
EMAIL_SUBJECT_PRIVATE_MESSAGE = 'You have a private message'
EMAIL_SUBJECT_SOUND_ADDED_AS_REMIX = 'Sound added as remix source'
EMAIL_SUBJECT_RANDOM_SOUND_OF_THE_SAY_CHOOSEN = 'One of your sounds has been chosen as random sound of the day!'
EMAIL_SUBJECT_NEW_COMMENT = 'You have a new comment'
EMAIL_SUBJECT_SOUND_FLAG = 'Sound flag'
EMAIL_SUBJECT_SUPPORT_EMAIL = '[support]'
EMAIL_SUBJECT_MODERATION_HANDLED = 'A Freesound moderator handled your upload'

# -------------------------------------------------------------------------------
# Static settings

# Add freesound/static/ to STATICFILES_DIRS as it won't be added by default (freesound/ is not an installed Django app)
STATICFILES_DIRS = [os.path.join(os.path.dirname(__file__), 'static'), ]
STATIC_URL = '/static/'
STATIC_ROOT = 'bw_static'
STORAGES = {
    "default": {
       "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": 'freesound.storage.NoStrictManifestStaticFilesStorage',
    },
}


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
FORUM_THREADS_PER_PAGE = 15
SOUND_COMMENTS_PER_PAGE = 5
SOUNDS_PER_PAGE = 15  # In search page
SOUNDS_PER_PAGE_COMPACT_MODE = 30  # In search page
PACKS_PER_PAGE = 15  # In search page
DOWNLOADED_SOUNDS_PACKS_PER_PAGE = 12
USERS_PER_DOWNLOADS_MODAL_PAGE = 15
COMMENTS_IN_MODAL_PER_PAGE = 15 
REMIXES_PER_PAGE = 10
MAX_TICKETS_IN_MODERATION_ASSIGNED_PAGE = 60
SOUNDS_PER_DESCRIBE_ROUND = 10
SOUNDS_PENDING_MODERATION_PER_PAGE = 9
MAX_UNMODERATED_SOUNDS_IN_HOME_PAGE = 5
DONATIONS_PER_PAGE = 40
FOLLOW_ITEMS_PER_PAGE = 5
MESSAGES_PER_PAGE = 10
BOOKMARKS_PER_PAGE = 12 
SOUNDS_PER_PAGE_PROFILE_PACK_PAGE = 12
NUM_SIMILAR_SOUNDS_PER_PAGE = 9
NUM_SIMILAR_SOUNDS_PAGES = 5


# Weights using to compute charts
BW_CHARTS_ACTIVE_USERS_WEIGHTS = {'upload': 1, 'post': 0.8, 'comment': 0.05}
CHARTS_DATA_CACHE_KEY = 'bw-charts-data'

# User profile page cache key templates
USER_STATS_CACHE_KEY = 'user_stats_{}'

# User flagging notification thresholds
USERFLAG_THRESHOLD_FOR_NOTIFICATION = 3
USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING = 6

# Supported audio formats
# When adding support for a new audio format you have to change the variables below and check:
# - mime types in accounts.forms.validate_file_extension
# - see if utils.audioprocessing.get_sound_type needs to be updated
# - add corresponding decoder to utils.audioprocessing.processing.convert_to_pcm (and of course add it to the docker image as well)
# - the audio analyzers will not need to be updated if the format is supported by ffmpeg
ALLOWED_AUDIOFILE_EXTENSIONS = ['wav', 'aiff', 'aif', 'ogg', 'flac', 'mp3', 'm4a', 'wv']
LOSSY_FILE_EXTENSIONS = ['ogg', 'mp3', 'm4a']
# Note that some SOUND_TYPE_CHOICES below might correspond to multiple extensions (aiff/aif > aiff)
SOUND_TYPE_CHOICES = (
    ('wav', 'Wave'),
    ('ogg', 'Ogg Vorbis'),
    ('aiff', 'AIFF'),
    ('mp3', 'Mp3'),
    ('flac', 'Flac'),
    ('m4a', 'M4a'),
    ('wv', 'WavPack'),
)
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

# Avatar background colors (only BW)
from utils.audioprocessing.processing import interpolate_colors
from utils.audioprocessing.color_schemes import BEASTWHOOSH_COLOR_SCHEME, COLOR_SCHEMES
AVATAR_BG_COLORS = interpolate_colors(COLOR_SCHEMES[BEASTWHOOSH_COLOR_SCHEME]['wave_colors'][1:], num_colors=10)

# Number of ratings of a sound to start showing average
MIN_NUMBER_RATINGS = 3

# Buffer size for CRC computation
CRC_BUFFER_SIZE = 4096

# Enable/disable uploading files (sounds, avatars) and describing sounds
UPLOAD_AND_DESCRIPTION_ENABLED = True

# Maximum combined file size for uploading files. This is set in nginx configuration
UPLOAD_MAX_FILE_SIZE_COMBINED = 1024 * 1024 * 1024  # 1 GB
MOVE_TMP_UPLOAD_FILES_INSTEAD_OF_COPYING = True

# Minimum number of sounds that a user has to upload before enabling bulk upload feature for that user
BULK_UPLOAD_MIN_SOUNDS = 40

# Turn this option on to log every time a user downloads a pack or sound
LOG_DOWNLOADS = False

# Use external CDN for downloading sounds (if sounds exist in the CDN) and serving previews/displays
USE_CDN_FOR_DOWNLOADS = False
USE_CDN_FOR_PREVIEWS = False
USE_CDN_FOR_DISPLAYS = False
CDN_DOWNLOADS_TEMPLATE_URL = 'https://cdn.freesound.org/sounds/{}/{}?filename={}'
CDN_PREVIEWS_URL = 'https://cdn.freesound.org/previews/'
CDN_DISPLAYS_URL = 'https://cdn.freesound.org/displays/'

# Followers notifications
MAX_EMAILS_PER_COMMAND_RUN = 5000
NOTIFICATION_TIMEDELTA_PERIOD = datetime.timedelta(days=7)

# Some other settings
ENABLE_QUERY_SUGGESTIONS = False
ENABLE_POPULAR_SEARCHES_IN_FRONTPAGE = False
ADVANCED_SEARCH_MENU_ALWAYS_CLOSED_ON_PAGE_LOAD = True
USER_DOWNLOADS_PUBLIC = True

ANNOUNCEMENT_CACHE_KEY = 'announcement_cache'

#-------------------------------------------------------------------------------
# Broad Sound Taxonomy definition

BROAD_SOUND_TAXONOMY = [
    {'key': 'm', 'level': 1, 'name': 'Music', 'description': 'Music excerpts, melodies, loops, fillers, drones and short musical snippets.'},
    {'key': 'm-sp', 'level': 2, 'name': 'Solo percussion', 'description': 'Music excerpts with solo percussive instruments.'},
    {'key': 'm-si', 'level': 2, 'name': 'Solo instrument', 'description': 'Music excerpts with only one instrument, excluding percussion.'},
    {'key': 'm-m', 'level': 2, 'name': 'Multiple instruments', 'description': 'Music excerpts with more than one instrument.'},
    {'key': 'm-other', 'level': 2, 'name': 'Other', 'description': 'Music that doesn\'t belong to any of the above categories.'},
    {'key': 'is', 'level': 1, 'name': 'Instrument samples', 'description': 'Single notes from musical instruments, various versions of the same note, and scales.'},
    {'key': 'is-p', 'level': 2, 'name': 'Percussion', 'description': 'Instrument samples that are percussive (idiophones or membraphones).'},
    {'key': 'is-s', 'level': 2, 'name': 'String', 'description': 'Instrument samples that belong to the string instrument family.'},
    {'key': 'is-w', 'level': 2, 'name': 'Wind', 'description': 'Instrument samples that belong to the wind instrument family (aerophones).'},
    {'key': 'is-k', 'level': 2, 'name': 'Piano / Keyboard instruments', 'description': 'Instrument samples of piano or other keyboard instruments, not synthesized.'},
    {'key': 'is-e', 'level': 2, 'name': 'Synths / Electronic', 'description': 'Instrument samples synthesized or produced by electronic means.'},
    {'key': 'is-other', 'level': 2, 'name': 'Other', 'description': 'Instrument samples that don\'t belong to any of the above categories.'},
    {'key': 'sp', 'level': 1, 'name': 'Speech', 'description': 'Sounds where human voice is prominent.'},
    {'key': 'sp-s', 'level': 2, 'name': 'Solo speech', 'description': 'Recording of a single voice speaking, excluding singing.'},
    {'key': 'sp-c', 'level': 2, 'name': 'Conversation / Crowd', 'description': 'Several people talking, having a conversation or dialogue.'},
    {'key': 'sp-p', 'level': 2, 'name': 'Processed / Synthetic', 'description': 'Voice(s) from an indirect source (e.g. radio), processed or synthesized.'},
    {'key': 'sp-other', 'level': 2, 'name': 'Other', 'description': 'Voice-predominant recordings that don\'t belong to any of the above categories.'},
    {'key': 'fx', 'level': 1, 'name': 'Sound effects', 'description': 'Isolated sound effects or sound events, each happening one at a time.'},
    {'key': 'fx-o', 'level': 2, 'name': 'Objects / House appliances', 'description': 'Everyday objects, inside the home or smaller in size.'},
    {'key': 'fx-v', 'level': 2, 'name': 'Vehicles', 'description': 'Sounds produced from a vehicle.'},
    {'key': 'fx-m', 'level': 2, 'name': 'Other mechanisms, engines, machines', 'description': 'Machine-like sounds, except vehicles and small house electric devices.'},
    {'key': 'fx-h', 'level': 2, 'name': 'Human sounds and actions', 'description': 'Sounds from the human body, excluding speech.'},
    {'key': 'fx-a', 'level': 2, 'name': 'Animals', 'description': 'Animal vocalizations or sounds.'},
    {'key': 'fx-n', 'level': 2, 'name': 'Natural elements and explosions', 'description': 'Sound events occuring by natural processes.'},
    {'key': 'fx-ex', 'level': 2, 'name': 'Experimental', 'description': 'Experimental sounds or heavily processed audio recordings.'},
    {'key': 'fx-el', 'level': 2, 'name': 'Electronic / Design', 'description': 'Sound effects that are computer-made or designed for user interfaces or animations.'},
    {'key': 'fx-other', 'level': 2, 'name': 'Other', 'description': 'Sound effects that don\'t belong to any of the above categories.'},
    {'key': 'ss', 'level': 1, 'name': 'Soundscapes', 'description': 'Ambiances, field-recordings with multiple events and sound environments.'},
    {'key': 'ss-n', 'level': 2, 'name': 'Nature', 'description': 'Soundscapes from natural habitats.'},
    {'key': 'ss-i', 'level': 2, 'name': 'Indoors', 'description': 'Soundscapes from closed or indoor spaces.'},
    {'key': 'ss-u', 'level': 2, 'name': 'Urban', 'description': 'Soundscapes from cityscapes or outdoor places with human intervention.'},
    {'key': 'ss-s', 'level': 2, 'name': 'Synthetic / Artificial', 'description': 'Soundscapes that are synthesized or computer-made ambiences.'},
    {'key': 'ss-other', 'level': 2, 'name': 'Other', 'description': 'Soundscapes that don\'t belong to any of the above categories.'},
]

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
BIRDNET_ANALYZER_NAME = 'birdnet_v1'
FSDSINET_ANALYZER_NAME = 'fsd-sinet_v1'
BST_ANALYZER_NAME = 'bst-extractor_v1'
 
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
    BIRDNET_ANALYZER_NAME: {
        'descriptors_map': [
            ('detections', 'birdnet_detections', None),  # Use None so detections are not indexed in solr but stored in database
            ('detected_classes', 'birdnet_detected_class', list),
            ('num_detections', 'birdnet_detections_count', int),
        ]
    },
    FSDSINET_ANALYZER_NAME: {
        'descriptors_map': [
            ('detections', 'fsdsinet_detections', None),  # Use None so detections are not indexed in solr but stored in database
            ('detected_classes', 'fsdsinet_detected_class', list),
            ('num_detections', 'fsdsinet_detections_count', int),
        ]
    },
    BST_ANALYZER_NAME: {
        'descriptors_map': [
            ('bst_top_level', 'category', str), 
            ('bst_second_level', 'subcategory', str),
        ]
    }
}

# -------------------------------------------------------------------------------
# Search engine

FCW_FILTER_VALUE = '("Attribution" OR "Creative Commons 0")'

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
SEARCH_SOUNDS_SORT_OPTION_DURATION_LONG_FIRST = "Duration (longest first)"
SEARCH_SOUNDS_SORT_OPTION_DURATION_SHORT_FIRST = "Duration (shortest first)"
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
SEARCH_SOUNDS_SORT_DEFAULT = SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC

SEARCH_SOUNDS_DEFAULT_FACETS = {
    SEARCH_SOUNDS_FIELD_SAMPLERATE: {'resort_by_value_as_int': True, 'skip_value_0': True},
    SEARCH_SOUNDS_FIELD_BITRATE: {'resort_by_value_as_int': True, 'skip_value_0': True},
    SEARCH_SOUNDS_FIELD_BITDEPTH: {'resort_by_value_as_int': True, 'skip_value_0': True},
    SEARCH_SOUNDS_FIELD_CHANNELS: {'resort_by_value_as_int': True, 'skip_value_0': True, 'limit': 10},
    SEARCH_SOUNDS_FIELD_PACK_GROUPING: {'limit': 10, 'title': 'Packs'},
    SEARCH_SOUNDS_FIELD_USER_NAME: {'limit': 10, 'widget': 'cloud', 'title': 'Users'},
    SEARCH_SOUNDS_FIELD_TAGS: {'limit': 30, 'widget': 'cloud'},
    SEARCH_SOUNDS_FIELD_TYPE: {'limit': len(SOUND_TYPE_CHOICES)},
    SEARCH_SOUNDS_FIELD_LICENSE_NAME: {'limit': 10},
}

SEARCH_SOUNDS_BETA_FACETS = {
    'category': {'limit': 30, 'title': 'Category'},
    'subcategory': {'limit': 30, 'title': 'Subcategory'},
    'fsdsinet_detected_class': {'limit': 30, 'title': 'FSD-SINet class'},
    'ac_brightness': {'type': 'range', 'start': 0, 'end': 100, 'gap': 20, 'widget': 'range', 'title': 'Brightness'},
    'ac_depth': {'type': 'range', 'start': 0, 'end': 100, 'gap': 20, 'widget': 'range', 'title': 'Depth'},
    'ac_warmth': {'type': 'range', 'start': 0, 'end': 100, 'gap': 20, 'widget': 'range', 'title': 'Warmth'},
    'ac_hardness': {'type': 'range', 'start': 0, 'end': 100, 'gap': 20, 'widget': 'range', 'title': 'Hardness'},
    'ac_boominess': {'type': 'range', 'start': 0, 'end': 100, 'gap': 20, 'widget': 'range', 'title': 'Boominess'},
}

SEARCH_FORUM_SORT_OPTION_THREAD_DATE_FIRST = "Thread creation (newest first)"
SEARCH_FORUM_SORT_OPTION_DATE_NEW_FIRST = "Post creation (newest first)"
SEARCH_FORUM_SORT_OPTIONS_WEB = [
    SEARCH_FORUM_SORT_OPTION_THREAD_DATE_FIRST,
    SEARCH_FORUM_SORT_OPTION_DATE_NEW_FIRST
]
SEARCH_FORUM_SORT_DEFAULT = SEARCH_FORUM_SORT_OPTION_THREAD_DATE_FIRST

SEARCH_ENGINE_BACKEND_CLASS = 'utils.search.backends.solr9pysolr.Solr9PySolrSearchEngine'
SOLR5_BASE_URL = "http://search:8983/solr"
SOLR9_BASE_URL = "http://search:8983/solr"

SEARCH_ENGINE_SIMILARITY_ANALYZERS = {
    BST_ANALYZER_NAME: {
        'vector_property_name': 'clap_embedding', 
        'vector_size': 512,
        'l2_norm': True
    },
    FSDSINET_ANALYZER_NAME: {
        'vector_property_name': 'embeddings', 
        'vector_size': 512,
        'l2_norm': True
    },
    FREESOUND_ESSENTIA_EXTRACTOR_NAME: {
        'vector_property_name': 'sim_vector', 
        'vector_size': 100,
        'l2_norm': True
    }
}
SEARCH_ENGINE_DEFAULT_SIMILARITY_ANALYZER = BST_ANALYZER_NAME
SEARCH_ENGINE_NUM_SIMILAR_SOUNDS_PER_QUERY = 500
USE_SEARCH_ENGINE_SIMILARITY = False

MAX_SEARCH_RESULTS_IN_MAP_DISPLAY = 10000  # This is the maximum number of sounds that will be shown when using "display results in map" mode

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
TRACES_SAMPLE_RATE = 0.1

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

# If not set, test keys will be used
# RECAPTCHA_PRIVATE_KEY = ''
# RECAPTCHA_PUBLIC_KEY = ''

# Google provides test keys which are set as the default for RECAPTCHA_PUBLIC_KEY and RECAPTCHA_PRIVATE_KEY.
# These cannot be used in production since they always validate to true and a warning will be shown on the reCAPTCHA.
# To bypass the security check that prevents the test keys from being used unknowingly add
# SILENCED_SYSTEM_CHECKS = [..., 'captcha.recaptcha_test_key_error', ...] to your settings.

SILENCED_SYSTEM_CHECKS += ['django_recaptcha.recaptcha_test_key_error']


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

# Used to configure output formats in newer FreesoundExtractor versions
ESSENTIA_PROFILE_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils/audioprocessing/essentia_profile.yaml'))

# Sound previews quality (for mp3, quality is in bitrate, for ogg, quality is in a number from 1 to 10  )
MP3_LQ_PREVIEW_QUALITY = 70
MP3_HQ_PREVIEW_QUALITY = 192
OGG_LQ_PREVIEW_QUALITY = 1
OGG_HQ_PREVIEW_QUALITY = 6

# -------------------------------------------------------------------------------
# Search results clustering
# NOTE: celery configuration is set after the local settings import

MAX_RESULTS_FOR_CLUSTERING = 1000

# One day timeout for keeping clustering results. The cache timer is reset when the clustering is 
# requested so that popular queries that are performed once a day minimum will always stay in cache
# and won't be recomputed.
CLUSTERING_CACHE_TIME = 24*60*60*1

# Limit of distance when creating Nearest Neighbors graph
CLUSTERING_MAX_NEIGHBORS_DISTANCE = 20

# Number of sound examples extracted per cluster for cluster facet sound preview
NUM_SOUND_EXAMPLES_PER_CLUSTER = 7

# Number of most common tags extracted per cluster for clustering facet name
NUM_TAGS_SHOWN_PER_CLUSTER = 3

# Number of maximum clusters to show to the user
CLUSTERING_NUM_MAX_CLUSTERS = 8

# Timeout for returning clustering results to the user
CLUSTERING_TASK_TIMEOUT = 30

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
    'CLIENT_ID_GENERATOR_CLASS': 'apiv2.apiv2_utils.FsClientIdGenerator',
    'PKCE_REQUIRED': False,
    'APPLICATION_ADMIN_CLASS': 'apiv2.oauth2_admin.ApplicationAdmin'
}
OAUTH2_PROVIDER_APPLICATION_MODEL = 'oauth2_provider.Application'

# APIv2 throttling limits
# Define API usage limit rates per defined throttling levels
# Possible time units: second, minute, hour or day
# Every level must include three limits, a burst limit, a sustained limit and an ip which are checked separately
# Burst limit sets the maximum number of requests that an api client can do in a minute
# Sustained limit sets the maximum number of requests that an api client can do in a day
# Ip limit sets the maximum number of requests from different ips that a client can do in an hour
APIV2_BASIC_THROTTLING_RATES_PER_LEVELS = {
    0: ['0/minute', '0/day', '0/hour'],  # Client 'disabled'
    1: ['60/minute', '2000/day', None],  # Ip limit not yet enabled
    2: ['300/minute', '5000/day', None],  # Ip limit not yet enabled
    3: ['300/minute', '15000/day', None],  # Ip limit not yet enabled
    99: [],  # No limit of requests
}
APIV2_POST_THROTTLING_RATES_PER_LEVELS = {
    0: ['0/minute', '0/day',  '0/hour'],  # Client 'disabled'
    1: ['30/minute', '500/day', None],  # Ip limit not yet enabled
    2: ['60/minute', '1000/day', None],  # Ip limit not yet enabled
    3: ['60/minute', '3000/day', None],  # Ip limit not yet enabled
    99: [],  # No limit of requests
}


# -------------------------------------------------------------------------------
# Frontend handling

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(os.path.dirname(__file__), '../templates'),
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
        }
    },
]

# -------------------------------------------------------------------------------
# Analytics
PLAUSIBLE_AGGREGATE_PAGEVIEWS = True

# -------------------------------------------------------------------------------
# Rabbit MQ 
RABBITMQ_USER = "guest"
RABBITMQ_PASS = "guest"
RABBITMQ_HOST = 'rabbitmq'
RABBITMQ_PORT = '5672'
RABBITMQ_API_PORT = '5673'


# -------------------------------------------------------------------------------
# Import local settings
# Important: place settings which depend on other settings potentially modified in local_settings.py BELOW the import
from .local_settings import *


# -------------------------------------------------------------------------------
# Celery
CELERY_BROKER_URL = f'amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}//'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/{CELERY_BROKER_REDIS_STORE_ID}'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ASYNC_TASKS_QUEUE_NAME = 'async_tasks_queue'
CELERY_SOUND_PROCESSING_QUEUE_NAME = 'sound_processing_queue'
CELERY_CLUSTERING_TASK_QUEUE_NAME = 'clustering_queue'


# -------------------------------------------------------------------------------
# Sentry

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        send_default_pii=True,
        traces_sample_rate=TRACES_SAMPLE_RATE,
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
PROCESSING_BEFORE_DESCRIPTION_DIR = os.path.join(DATA_PATH, "processing_before_description/")

# URLs (depend on DATA_URL potentially re-defined in local_settings.py)
AVATARS_URL = DATA_URL + "avatars/"
PREVIEWS_URL = DATA_URL + "previews/"
DISPLAYS_URL = DATA_URL + "displays/"
ANALYSIS_URL = DATA_URL + "analysis/"
PROCESSING_BEFORE_DESCRIPTION_URL = DATA_URL + "processing_before_description/"

# In a typical development setup original files won't be available in the filesystem, but preview files
# might be available as these take much less space. The flag below will configure Freesound to use these
# preview files (instead of the originals) for processing and downloading when the originals are not available.
USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING = DEBUG

if DEBUG and DISPLAY_DEBUG_TOOLBAR:
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INSTALLED_APPS += ['debug_toolbar']

    DEBUG_TOOLBAR_PANELS = [
        'debug_toolbar.panels.history.HistoryPanel',
        'debug_toolbar.panels.versions.VersionsPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
        'debug_toolbar.panels.templates.TemplatesPanel',
        'debug_toolbar.panels.alerts.AlertsPanel',
        'debug_toolbar.panels.cache.CachePanel',
        'debug_toolbar.panels.signals.SignalsPanel',
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
from .logger import LOGGING
