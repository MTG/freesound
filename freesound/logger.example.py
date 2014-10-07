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
        'clickusagelogfile': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/var/log/freesound/clickusage.log',
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
        'gearman_worker_processing_handler': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/var/log/freesound/gearman_worker_processing.log',
            'when': 'midnight',
            'backupCount': '14',
            'formatter': 'standard'
        },
        'gelf_gearman_worker_processing': {
            'class': 'graypy.GELFHandler',
            'host': '10.55.0.20',
            'port': 12201,
            'formatter': 'standard'
        },
        'processing_handler': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': '/var/log/freesound/audio_processing.log',
            'when': 'midnight',
            'backupCount': '14',
            'formatter': 'standard'
        },
        'gelf_processing': {
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
            'handlers': ['audioprocessinglogfile'],
            'level': 'INFO',
            'propagate': False,
        },
        'api': {
            'handlers': ['api'],
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
        'clickusage': {
            'handlers': ['clickusagelogfile'],
            'level': 'INFO',
            'propagate': False,
        },
        'upload': {
            'handlers': ['uploadlogfile'],
            'level': 'INFO',
            'propagate': False,
        },
        'processing': {
            'handlers': ['processing_handler'],
            'level': 'INFO',
            'propagate': False,
        },
        'gearman_worker_processing': {
            'handlers': ['gearman_worker_processing_handler'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
