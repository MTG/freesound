# -*- coding: utf-8 -*-

# Django settings for freesound project.
import os

DEBUG = False

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'context_processor.context_extra',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
    #'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.middleware.locale.LocaleMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.flatpages',
    'django.contrib.markup',
    'django_extensions',
    'accounts',
    'comments',
    'favorites',
    'geotags',
    'general',
    'images',
    'messages',
    'ratings',
    'sounds',
    'support',
    'tags',
    'forum',
    'wiki'
)

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(os.path.dirname(__file__), 'templates'),
)

# Email that error messages come from
SERVER_EMAIL = 'devnull@iua.upf.edu'

DATABASE_ENGINE = 'postgresql_psycopg2'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'freesound'             # Or path to database file if using sqlite3.
DATABASE_USER = 'freesound'             # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

TIME_ZONE = 'Europe/Brussels'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

CACHE_BACKEND = 'memcached://127.0.0.1:11211/'
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = 'freesound'

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

ROOT_URLCONF = 'urls'

AUTH_PROFILE_MODULE = 'accounts.Profile'
LOGIN_URL = '/account/login/'

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'media')

DEFAULT_FROM_EMAIL = 'The Freesound Bot <devnull@iua.upf.edu>'
EMAIL_HOST = 'iua-mail.upf.edu'
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_SUBJECT_PREFIX = 'Freesound. '

SEND_BROKEN_LINK_EMAILS = False

IGNORABLE_404_STARTS = ('/cgi-bin/', '/_vti_bin', '/_vti_inf')
IGNORABLE_404_ENDS = ('.jsp', 'mail.pl', 'mailform.pl', 'mail.cgi', 'mailform.cgi', 'favicon.ico', '.php')

# A tuple of IP addresses, as strings, that:
# See debug comments, when DEBUG is True
INTERNAL_IPS = ['localhost', '127.0.0.1']


FREESOUND_RSS = "http://www.freesound.org/blog/?feed=rss2"
FORUM_POSTS_PER_PAGE = 20
FORUM_THREADS_PER_PAGE = 40
FILES_UPLOAD_DIRECTORY = "/freesound/uploads/"
FILES_UPLOAD_OK_DIRECTORY = "/freesound/uploads_ok/"

# urls for which the "lasta ction time" needs updating
LAST_ACTION_TIME_URLS = ('/forum/', )


# leave at bottom starting here!
from local_settings import *

print "TODO: create logging sinks in settings.py"

TEMPLATE_DEBUG = DEBUG

if DEBUG:
    MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware',)
    INSTALLED_APPS += ('debug_toolbar',)
    
    DEBUG_TOOLBAR_PANELS = (
        'debug_toolbar.panels.sql.SQLDebugPanel',
        'debug_toolbar.panels.headers.HeaderDebugPanel',
        'debug_toolbar.panels.cache.CacheDebugPanel',
        'debug_toolbar.panels.profiler.ProfilerDebugPanel',
        'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
        'debug_toolbar.panels.templates.TemplatesDebugPanel',
        # If you are using the profiler panel you don't need the timer
        # 'debug_toolbar.panels.timer.TimerDebugPanel',
    )
