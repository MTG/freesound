'''
Created on Dec 12, 2011

@author: stelios
'''

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'worker': {
            'format': '%(asctime)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'errorlogfile': {
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': '/var/log/freesound/error500.log',
        },
        'stderr': {
            'class': 'logging.StreamHandler'
        },
        'audioprocessinglogfile': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/var/log/freesound/audio.log',
            'when': 'midnight',
            'backupCount': '14',
            'formatter': 'worker'
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
            'handlers': ['errorlogfile'],
            'level': 'ERROR',   # only catches 5xx not 4xx messages
            'propagate': True,
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
