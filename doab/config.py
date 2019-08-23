import logging.config


def init_logging(debug=False):
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'root': {
            'level': 'DEBUG' if debug else 'INFO',
            'handlers': ['console'],
        },
        'formatters': {
            'default': {
                'format': '%(levelname)s %(asctime)s %(module)s '
                'P:%(process)d T:%(thread)d %(message)s',
            },
            'coloured': {
                '()': 'colorlog.ColoredFormatter',
                'format': '%(log_color)s%(levelname)s %(asctime)s %(module)s '
                'P:%(process)d T:%(thread)d %(message)s',
                'log_colors': {
                    'DEBUG':    'green',
                    'WARNING':  'yellow',
                    'ERROR':    'red',
                    'CRITICAL': 'purple',
                },
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG' if debug else 'INFO',
                'formatter': 'coloured',
                'stream': 'ext://sys.stdout',
            },
        },
        'loggers': {
            'sqlalchemy': {
                'level': 'WARNING',
                'handlers': ['console'],
            },
        },
    }

    logging.config.dictConfig(logging_config)
