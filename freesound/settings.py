# -*- coding: utf-8 -*-

# Test comment

# Django settings for freesound project.
import os
import datetime
import re
import logging.config

DEBUG = False

MIDDLEWARE = [
    'freesound.middleware.PermissionDeniedHandler',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'freesound.middleware.OnlineUsersHandler',
    'corsheaders.middleware.CorsMiddleware',
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
    'general',
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
    'utils',  # So that we also run utils tests
    'donations',
    'monitor',
    'raven.contrib.django.raven_compat',
    'django_object_actions',
    #'test_utils', # Don't use this in production!
]

CORS_ORIGIN_ALLOW_ALL = True
AUTHENTICATION_BACKENDS = ('accounts.modelbackend.CustomModelBackend',)

# Email settings
SERVER_EMAIL = 'noreply@freesound.org'
EMAIL_SUBJECT_PREFIX = '[freesound] '
SEND_BROKEN_LINK_EMAILS = True
DEFAULT_FROM_EMAIL = 'Freesound NoReply <noreply@freesound.org>'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25

# This was the default serializer in django 1.6. Now we keep using it because
# we saw some erros when running tests, in the future we should change to the
# new one.
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

TIME_ZONE = 'Europe/Brussels'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_X_FORWARDED_HOST = True

# Not using django timezones as project originally with Django 1.3. We might fix this in the future:  https://docs.djangoproject.com/en/1.5/topics/i18n/timezones/#time-zones-migration-guide
USE_TZ = False

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

#CACHE_BACKEND = 'memcached://127.0.0.1:11211/'
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = 'freesound'

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

ROOT_URLCONF = 'freesound.urls'

WSGI_APPLICATION = 'freesound.wsgi.application'

# This configuration is not used by django anymore
AUTH_PROFILE_MODULE = 'accounts.Profile'

LOGIN_URL = '/home/login/'
LOGOUT_URL = '/home/logout/'
LOGIN_REDIRECT_URL = '/home/'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')

#IGNORABLE_404_STARTS = ('/cgi-bin/', '/_vti_bin', '/_vti_inf', '/favicon')
#IGNORABLE_404_ENDS = ('.jsp', 'mail.pl', 'mailform.pl', 'mail.cgi', 'mailform.cgi', '.php', 'similar')
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

# Silence Django system check urls.W002 "Your URL pattern '/$' has a regex beginning with a '/'.
# Remove this slash as it is unnecessary." triggered in API urls. Although the check claims the last
# slash is not necessary, it is in our case as otherwise it breaks some API urls when these don't end
# with slash.
SILENCED_SYSTEM_CHECKS = ['urls.W002']

# A tuple of IP addresses, as strings, that:
# See debug comments, when DEBUG is True
INTERNAL_IPS = ['localhost', '127.0.0.1']

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(os.path.dirname(__file__), '../freesound/../media')
MEDIA_URL = "/media/"

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
ADMIN_MEDIA_PREFIX = '/media/admin_media/'
STATIC_URL = '/media/admin_media/'

FILES_UPLOAD_DIRECTORY = os.path.join(os.path.dirname(__file__), 'uploads')

# urls for which the "lasta ction time" needs updating
LAST_ACTION_TIME_URLS = ('/forum/', )

IFRAME_PLAYER_SIZE = {
        'large': [920, 245],
        'medium': [481, 86],
        'small': [375, 30],
        'twitter_card': [440, 132]
    }

FREESOUND_RSS = "http://10.55.0.51/?feed=rss2" #"http://blog.freesound.org/?feed=rss2"

FORUM_POSTS_PER_PAGE = 20
FORUM_THREADS_PER_PAGE = 40
SOUND_COMMENTS_PER_PAGE = 5
SOUNDS_PER_PAGE = 15
PACKS_PER_PAGE = 15
REMIXES_PER_PAGE = 10
SOUNDS_PER_API_RESPONSE = 30
MAX_SOUNDS_PER_API_RESPONSE = 100
SOUNDS_PER_DESCRIBE_ROUND = 10
USERFLAG_THRESHOLD_FOR_NOTIFICATION = 3
USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING = 6
MAX_TICKETS_IN_MODERATION_ASSIGNED_PAGE = 30
SOUNDS_PENDING_MODERATION_PER_PAGE = 8
MAX_UNMODERATED_SOUNDS_IN_HOME_PAGE = 5
ALLOWED_AUDIOFILE_EXTENSIONS = ['wav', 'aiff', 'aif', 'ogg', 'flac', 'mp3', 'm4a']

# Number of ratings of a sound to start showing average
MIN_NUMBER_RATINGS = 3

# Graylog stream ids and domain
GRAYLOG_API_STREAM_ID = '530f2ec5e4b0f124869546d0'
GRAYLOG_SEARCH_STREAM_ID = '531051bee4b0f1248696785a'
GRAYLOG_DOMAIN = 'http://mtg-logserver.s.upf.edu'

# COOKIE_LAW_EXPIRATION_TIME change in freesound.js (now is 360 days)
# $.cookie("cookieConsent", "yes", { expires: 360, path: '/' });

DELETED_USER_ID = 1

DISPLAY_DEBUG_TOOLBAR = False # change this in the local_settings

#-------------------------------------------------------------------------------
# freesound paths and urls:

DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../freesound-data/'))
AVATARS_PATH = os.path.join(DATA_PATH, "avatars/")
PREVIEWS_PATH = os.path.join(DATA_PATH, "previews/")
DISPLAYS_PATH = os.path.join(DATA_PATH, "displays/") # waveform and spectrum views
SOUNDS_PATH = os.path.join(DATA_PATH, "sounds/")
PACKS_PATH = os.path.join(DATA_PATH, "packs/")
UPLOADS_PATH = os.path.join(DATA_PATH, "uploads/")
ANALYSIS_PATH = os.path.join(DATA_PATH, "analysis/")
FILE_UPLOAD_TEMP_DIR = os.path.join(DATA_PATH, "tmp_uploads/")

SENDFILE_SECRET_URL = "/secret/"
SOUNDS_SENDFILE_URL = SENDFILE_SECRET_URL + "sounds/"
PACKS_SENDFILE_URL = SENDFILE_SECRET_URL + "packs/"

#-------------------------------------------------------------------------------

STEREOFY_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../_sandbox/stereofy/stereofy'))

SESSION_COOKIE_DOMAIN = None # leave this until you know what you are doing

ESSENTIA_EXECUTABLE = '/home/fsweb/freesound/essentia/streaming_extractor_freesound'

# APIV2 settings
################

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
}

DOWNLOAD_TOKEN_LIFETIME = 60*60  # 1 hour

# APIv2 throttling limits are defined in local_settings

# Oauth2 provider settings
OAUTH2_PROVIDER = {
    'ACCESS_TOKEN_EXPIRE_SECONDS': 60*60*24,
    'CLIENT_SECRET_GENERATOR_LENGTH': 40,
    'AUTHORIZATION_CODE_EXPIRE_SECONDS': 10*60,
    'OAUTH2_VALIDATOR_CLASS': 'apiv2.oauth2_validators.OAuth2Validator',
    'REQUEST_APPROVAL_PROMPT': 'auto',
    'CLIENT_ID_GENERATOR_CLASS': 'apiv2.apiv2_utils.FsClientIdGenerator'
}
OAUTH2_PROVIDER_APPLICATION_MODEL = 'oauth2_provider.Application'

# Set DATA_URL. You can overwrite this to point to production data ("http://freesound.org/data/") in
# local settings if needed ;)
DATA_URL = "/data/"

# Locations where sounds, previews and other "static" content will be mirrored (if specified)
# If locations do not exist, they will be created
MIRROR_SOUNDS = None  # list of locations to mirror contents of SOUNDS_PATH, set to None to turn off
MIRROR_PREVIEWS = None  # list of locations to mirror contents of SOUNDS_PATH, set to None to turn off
MIRROR_DISPLAYS = None  # list of locations to mirror contents of SOUNDS_PATH, set to None to turn off
MIRROR_ANALYSIS = None  # list of locations to mirror contents of SOUNDS_PATH, set to None to turn off
MIRROR_AVATARS = None  # list of locations to mirror contents of AVATARS_PATH, set to None to turn off
MIRROR_UPLOADS = None  # list of locations to mirror contents of MIRROR_UPLOADS, set to None to turn off
LOG_START_AND_END_COPYING_FILES = True


# leave at bottom starting here!
from local_settings import *

if DEBUG:
    # We name this CONF_ because Django system check thinks that a variable
    # called TEMPLATE_LOADERS is pre-1.8 Django configuration.
    CONF_TEMPLATE_LOADERS = [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]
else:
    CONF_TEMPLATE_LOADERS = [
        ('django.template.loaders.cached.Loader', [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ]),
    ]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(os.path.dirname(__file__), '../templates')
        ],
        'OPTIONS': {
            'loaders': CONF_TEMPLATE_LOADERS,
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
    },
]

AVATARS_URL = DATA_URL + "avatars/"
PREVIEWS_URL = DATA_URL + "previews/"
DISPLAYS_URL = DATA_URL + "displays/"
ANALYSIS_URL = DATA_URL + "analysis/"

if DEBUG and DISPLAY_DEBUG_TOOLBAR:
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INSTALLED_APPS += ['debug_toolbar']
    #INTERNAL_IPS +=('127.0.0.1', 'localhost')

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
    }

MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'


# We use the last restart date as a timestamp of the last time freesound web was restarted (lat time
# settings were loaded). We add this variable to the context processor and use it in base.html as a
# parameter for the url of all.css and freesound.js files, so me make sure client browsers update these
# files when we do a deploy (the url changes)
LAST_RESTART_DATE = datetime.datetime.now().strftime("%d%m")

# Followers notifications
MAX_EMAILS_PER_COMMAND_RUN = 1000
NOTIFICATION_TIMEDELTA_PERIOD = datetime.timedelta(days=7)

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
]

from logger import LOGGING
