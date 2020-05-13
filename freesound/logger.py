LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] # %(levelname)s    # %(message)s'
        }
    },
    'filters': {
        'api_filter': {
            '()': 'utils.logging_filters.APILogsFilter',
        },
        'generic_data_filter': {
            '()': 'utils.logging_filters.GenericDataFilter'
        }
    },
    'handlers': {
        'stdout': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
    },
    'loggers': {
        'console': {
            'handlers': ['stdout'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['stdout'],
            'level': 'ERROR',   # only catches 5xx not 4xx messages
            'propagate': True,
        },
        'sounds': {
            'handlers': ['stdout'],
            'level': 'INFO',
            'propagate': False,
        },
        'api': {
            'handlers': ['stdout'],
            'level': 'INFO',
            'propagate': False,
        },
        'api_errors': {
            'handlers': ['stdout'],
            'level': 'INFO',
            'propagate': False,
        },
        'emails': {
            'handlers': ['stdout'],
            'level': 'INFO',
            'propagate': False,
        },
        'web': {
            'handlers': ['stdout'],
            'level': 'INFO',
            'propagate': False,
        },
        'search': {
            'handlers': ['stdout'],
            'level': 'INFO',
            'propagate': False,
        },
        'file_upload': {
            'handlers': ['stdout'],
            'level': 'INFO',
            'propagate': False,
        },
        'workers': {
            'handlers': ['stdout'],
            'level': 'INFO',
            'propagate': False,
        },
        'commands': {
            'handlers': ['stdout'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
