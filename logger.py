'''
Created on Dec 12, 2011

@author: stelios
'''

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] # %(levelname)s    # %(message)s'
        },
        'worker': {
            'format': '[%(asctime)s] # %(levelname)s    # [%(process)d] %(message)s'
        },
    },
    'handlers': {
        'errorlogfile': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/var/log/freesound/error500.log',
            'when': 'midnight',
            'backupCount': '14',
            'formatter': 'standard'
        },
        'gelf_error': {
            'class': 'graypy.GELFHandler',
            'host': '10.55.0.20',
            'port': 12201,
            'formatter': 'standard'
        },
        'stderr': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        'audioprocessinglogfile': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/var/log/freesound/audio.log',
            'when': 'midnight',
            'backupCount': '14',
            'formatter': 'worker'
        },
        'gelf_audio': {
            'class': 'graypy.GELFHandler',
            'host': '10.55.0.20',
            'port': 12201,
            'formatter': 'worker'
        },
        'weblogfile': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/var/log/freesound/web.log',
            'when': 'midnight',
            'backupCount': '14',
            'formatter': 'standard'
        },
        'gelf_web': {
            'class': 'graypy.GELFHandler',
            'host': '10.55.0.20',
            'port': 12201,
            'formatter': 'standard'
        },
        'api': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/var/log/freesound/api.log',
            'when': 'midnight',
            'backupCount': '14',
            'formatter': 'standard'
        },
        'gelf_api': {
            'class': 'graypy.GELFHandler',
            'host': '10.55.0.20',
            'port': 12201,
            'formatter': 'standard'
        },
        'searchlogfile': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/var/log/freesound/search.log',
            'when': 'midnight',
            'backupCount': '14',
            'formatter': 'standard'
        },
        'gelf_search': {
            'class': 'graypy.GELFHandler',
            'host': '10.55.0.20',
            'port': 12201,
            'formatter': 'standard'
        },
        'uploadlogfile': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/var/log/freesound/upload.log',
            'when': 'midnight',
            'backupCount': '14',
            'formatter': 'standard'
        },
        'gelf_upload': {
            'class': 'graypy.GELFHandler',
            'host': '10.55.0.20',
            'port': 12201,
            'formatter': 'standard'
        },
        'mail': {
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': '/var/log/freesound/mail.log',
            'formatter': 'standard'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['errorlogfile'],
            'level': 'ERROR',   # only catches 5xx not 4xx messages
            'propagate': True,
        },
        'audio': {
            'handlers': ['audioprocessinglogfile','gelf_audio'],
            'level': 'INFO',
            'propagate': False,
        },
        'api': {
            'handlers': ['api','gelf_api'],
            'level': 'INFO',
            'propagate': False,
        },
        'web': {
            'handlers': ['weblogfile','gelf_web'],
            'level': 'INFO',
            'propagate': False,
        },
        'search': {
            'handlers': ['searchlogfile','gelf_search'],
            'level': 'INFO',
            'propagate': False,
        },
        'upload': {
            'handlers': ['uploadlogfile','gelf_upload'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
