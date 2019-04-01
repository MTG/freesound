from settings import *

postgres_username = os.getenv('FS_TEST_PG_USERNAME', None)
if postgres_username is not None:
    DATABASES['default']['NAME'] = 'freesound'
    DATABASES['default']['USER'] = postgres_username

use_django_nose = os.getenv('FS_TEST_USE_DJANGO_NOSE', None)
if use_django_nose is not None:
    INSTALLED_APPS = INSTALLED_APPS + ('django_nose',)
    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
    SOUTH_TESTS_MIGRATE = False
    NOSE_ARGS = [
        '--with-xunit',
    ]

SECRET_KEY = "testsecretwhichhastobeatleast16characterslong"
RAVEN_CONFIG = {}
SUPPORT = (('Name Surname', 'support@freesound.org'),)
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
