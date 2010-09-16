# -*- coding: utf-8 -*-

DEBUG = True

ADMINS = (
    ('Bram de Jong', 'support@freesound.org'),
)

DATABASE_ENGINE = 'sqlite'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'freesound'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.
DATABASE_PASSWORD = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = 'http://localhost:8080/fsmedia/'

# data URL, hosted via lighttpd or something similar
DATA_URL = MEDIA_URL + 'data/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/admin_media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

EMAIL_HOST = 'localhost'
EMAIL_PORT = 2525
#EMAIL_HOST_USER = ''
#EMAIL_HOST_PASSWORD = ''

SESSION_COOKIE_DOMAIN = None # leave this until you know what you are doing

PROXIES = {}
#PROXIES = {'http': 'http://proxy.upf.edu:8080'}

RECAPTCHA_PRIVATE_KEY = ''
RECAPTCHA_PUBLIC_KEY = ''

GOOGLE_API_KEY = ''

SOLR_URL = "http://localhost:8983/solr/"

DISPLAY_DEBUG_TOOLBAR = False # change this in the local_settings

STEREOFY_PATH = "/home/fsweb/freesound/sandbox/legacy/stereofy/stereofy"
