from settings import *

DATABASES['default']['NAME'] = 'freesound'
DATABASES['default']['USER'] = 'freesound'
INSTALLED_APPS = INSTALLED_APPS + ('django_nose', )
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
SOUTH_TESTS_MIGRATE = False
NOSE_ARGS = [
    '--with-xunit',
]
SECRET_KEY = "testsecretwhichhastobeatleast16characterslong"
