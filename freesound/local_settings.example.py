# -*- coding: utf-8 -*-

import os

DEBUG = True

ADMINS = (
    ('Bram de Jong', 'support@freesound.org'),
)

DATABASE_PASSWORD = 'x'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/admin_media/'

# data path, where all files should go to
DATA_PATH = '/Users/bram/Development/nightingale/freesound/media/data/'

# data URL, hosted via lighttpd or something similar
DATA_URL = MEDIA_URL + 'data/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '....something unique and long here....'

EMAIL_HOST = 'localhost'
EMAIL_PORT = 2525

SESSION_COOKIE_DOMAIN = None # leave this until you know what you are doing

# place where files will be uploaded to via HTTP (and FTP)
FILES_UPLOAD_DIRECTORY = "/Users/bram/Development/nightingale/freesound/uploads/uploads/"
FILES_UPLOAD_OK_DIRECTORY = "/Users/bram/Development/nightingale/freesound/uploads/uploads_ok/"

PROXIES = {} #{'http': 'http://proxy.upf.edu:8080'}

RECAPTCHA_PRIVATE_KEY = 'your recaptcha private key'
RECAPTCHA_PUBLIC_KEY = 'your recaptcha public key'

GOOGLE_API_KEY = 'your google maps api key'