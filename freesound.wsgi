import os, sys

sys.path.append('/Users/bram/Development/nightingale/freesound')
sys.path.append('/Users/bram/Development/nightingale')

os.environ['DJANGO_SETTINGS_MODULE'] = 'freesound.settings'

import django.core.handlers.wsgi

application = django.core.handlers.wsgi.WSGIHandler()
