# -*- coding: utf-8 -*-

# Test comment

# Django settings for freesound project.
import os
import logging.config

DEBUG = True

TEMPLATE_CONTEXT_PROCESSORS = (
    # 'django.core.context_processors.auth',
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.contrib.messages.context_processors.messages',
    'context_processor.context_extra',
)

MIDDLEWARE_CLASSES = (
    'middleware.PermissionDeniedHandler',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'middleware.BulkChangeLicenseHandler',
    #'django.middleware.locale.LocaleMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'middleware.OnlineUsersHandler'
)

INSTALLED_APPS = (
    'messages',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.flatpages',
    'django.contrib.markup',
    'django.contrib.messages',
    'south',
    'geotags',
    'accounts',
    'comments',
    'ratings',
    'tags',
    'general',
    'support',
    'wiki',
    'favorites',
    'sounds',
    'bookmarks',
    'forum',
    'search',
    'api',
    'django_extensions',
    'tickets',
    'gunicorn', 
    'usage',
    #'test_utils', # Don't use this in production!
)

AUTHENTICATION_BACKENDS = ('accounts.modelbackend.CustomModelBackend',)

TEMPLATE_DIRS = (
    # Myles' template directory is here because it allows him to work on tabasco.
    '/home/mdebastion/templates',
    os.path.join(os.path.dirname(__file__), 'templates'),
)

# Email settings
SERVER_EMAIL = 'noreply@freesound.org'
EMAIL_SUBJECT_PREFIX = '[freesound] '
SEND_BROKEN_LINK_EMAILS = True
DEFAULT_FROM_EMAIL = 'Freesound NoReply <noreply@freesound.org>'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25

TIME_ZONE = 'Europe/Brussels'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

#CACHE_BACKEND = 'memcached://127.0.0.1:11211/'
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = 'freesound'

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

ROOT_URLCONF = 'urls'

AUTH_PROFILE_MODULE = 'accounts.Profile'
LOGIN_URL = '/home/login/'
LOGOUT_URL = '/home/logout/'
LOGIN_REDIRECT_URL = '/home/'

IGNORABLE_404_STARTS = ('/cgi-bin/', '/_vti_bin', '/_vti_inf', '/favicon')
IGNORABLE_404_ENDS = ('.jsp', 'mail.pl', 'mailform.pl', 'mail.cgi', 'mailform.cgi', '.php', 'similar')

# A tuple of IP addresses, as strings, that:
# See debug comments, when DEBUG is True
INTERNAL_IPS = ['localhost', '127.0.0.1']

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'media')
MEDIA_URL = "/media/"

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
ADMIN_MEDIA_PREFIX = '/media/admin_media/'


FILES_UPLOAD_DIRECTORY = os.path.join(os.path.dirname(__file__), 'uploads')

# urls for which the "lasta ction time" needs updating
LAST_ACTION_TIME_URLS = ('/forum/', )

FREESOUND_RSS = "http://blog.freesound.org/?feed=rss2"

FORUM_POSTS_PER_PAGE = 20
FORUM_THREADS_PER_PAGE = 40
SOUND_COMMENTS_PER_PAGE = 5
SOUNDS_PER_PAGE = 15
PACKS_PER_PAGE = 15
REMIXES_PER_PAGE = 10
SOUNDS_PER_API_RESPONSE = 30
MAX_SOUNDS_PER_API_RESPONSE = 100
SOUNDS_PER_DESCRIBE_ROUND = 4
USERFLAG_THRESHOLD_FOR_NOTIFICATION = 3
USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING = 6

DELETED_USER_ID = 1


DISPLAY_DEBUG_TOOLBAR = False # change this in the local_settings

#-------------------------------------------------------------------------------
# freesound paths and urls:

DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../freesound-data/'))
AVATARS_PATH = os.path.join(DATA_PATH, "avatars/")
PREVIEWS_PATH = os.path.join(DATA_PATH, "previews/")
DISPLAYS_PATH = os.path.join(DATA_PATH, "displays/") # waveform and spectrum views
SOUNDS_PATH = os.path.join(DATA_PATH, "sounds/")
PACKS_PATH = os.path.join(DATA_PATH, "packs/")
UPLOADS_PATH = os.path.join(DATA_PATH, "uploads/")
ANALYSIS_PATH = os.path.join(DATA_PATH, "analysis/")

SENDFILE_SECRET_URL = "/secret/"
SOUNDS_SENDFILE_URL = SENDFILE_SECRET_URL + "sounds/"
PACKS_SENDFILE_URL = SENDFILE_SECRET_URL + "packs/"

#-------------------------------------------------------------------------------

STEREOFY_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '_sandbox/stereofy/stereofy'))

SESSION_COOKIE_DOMAIN = None # leave this until you know what you are doing

# leave at bottom starting here!
from local_settings import *

TEMPLATE_DEBUG = DEBUG
MANAGERS = ADMINS

# Only cache templates in production
if DEBUG:
    TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.load_template_source',
        'django.template.loaders.app_directories.load_template_source',
    )
else:
    TEMPLATE_LOADERS = (
        ('django.template.loaders.cached.Loader', (
            'django.template.loaders.filesystem.load_template_source',
            'django.template.loaders.app_directories.load_template_source',
            #'django.template.loaders.eggs.load_template_source',
        )),
    )

# change the media url to tabasco to make the players work when testing
if DEBUG:
    #DATA_URL = "http://freesound.org/data/"
    DATA_URL = "/data/"
else:
    DATA_URL = "/data/"

AVATARS_URL = DATA_URL + "avatars/"
PREVIEWS_URL = DATA_URL + "previews/"
DISPLAYS_URL = DATA_URL + "displays/"
ANALYSIS_URL = DATA_URL + "analysis/"

if DEBUG and DISPLAY_DEBUG_TOOLBAR:
    MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware',)
    INSTALLED_APPS += ('debug_toolbar',)
    INTERNAL_IPS +=('127.0.0.1', 'localhost')

    DEBUG_TOOLBAR_PANELS = (
        'debug_toolbar.panels.version.VersionDebugPanel',
        'debug_toolbar.panels.timer.TimerDebugPanel',
        'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
        'debug_toolbar.panels.headers.HeaderDebugPanel',
        'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
        'debug_toolbar.panels.template.TemplateDebugPanel',
        'debug_toolbar.panels.sql.SQLDebugPanel',
        'debug_toolbar.panels.signals.SignalDebugPanel',
        'debug_toolbar.panels.logger.LoggingPanel',
        'debug_toolbar.panels.cache.CacheDebugPanel'
    )

    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
    }

MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'

ESSENTIA_EXECUTABLE = '/home/fsweb/freesound/essentia/essentia_1.2.2_extractor/streaming_extractor'

from logger import LOGGING
