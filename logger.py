'''
Created on Dec 12, 2011

@author: stelios
'''

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'errorlogfile': {
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': '/var/log/freesound/error500.log'
        },
        'testlogfile': {
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': '/var/log/freesound/testlog.log'
        },
        'stderr': {
            'class': 'logging.StreamHandler'
        },
        'audioprocessinglogfile': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/var/log/freesound/audio.log',
            'when': 'midnight',
            'backupCount': '14'
        },
        'weblogfile': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/var/log/freesound/web.log',
            'when': 'midnight',
            'backupCount': '14'
        },
        'searchlogfile': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/var/log/freesound/search.log',
            'when': 'midnight',
            'backupCount': '14'
        },
        'uploadlogfile': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/var/log/freesound/upload.log',
            'when': 'midnight',
            'backupCount': '14'
        },
        'mail': {
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': '/var/log/freesound/mail.log'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['testlogfile'],
            'level': 'INFO',
            'propagate': True,
        },
        'django': {
            'handlers': ['errorlogfile'],
            'level': 'ERROR',
            'propagate': False,
        },
        
        'processing': {
            'handlers': ['audioprocessinglogfile'],
            'level': 'INFO',
            'propagate': False,
        },
        'web': {
            'handlers': ['weblogfile'],
            'level': 'INFO',
            'propagate': False,
        },
        'search': {
            'handlers': ['searchlogfile'],
            'level': 'INFO',
            'propagate': False,
        },
        'upload': {
            'handlers': ['uploadlogfile'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
