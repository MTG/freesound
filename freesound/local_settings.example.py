# -*- coding: utf-8 -*-

DEBUG = True

ADMINS = (
    ('Your Name', 'Your Email'),
)

MANAGERS = ADMINS

DATABASE_PASSWORD = 'password'

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = '/absolute/path/to/nightingale/trunk/freesound/media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = 'http://127.0.0.1:8000/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = 'http://127.0.0.1:8000/media/admin_media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'pgfwcaswp$ss(d@yn)!k)x#9tbgy!d!y59mwj4s4min^ft+hx)'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    '/absolute/path/to/nightingale/trunk/freesound/templates'
)

EMAIL_HOST_USER = '' # your iua username
EMAIL_HOST_PASSWORD = '' # your iua password

SESSION_COOKIE_DOMAIN = None # leave this until you know what you are doing