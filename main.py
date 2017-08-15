import logging
from logging.handlers import RotatingFileHandler
from bot import create_app
import config

def config_logger():
    logger = logging.getLogger()
    if config.APP_LOG_FILE != '':
        handler = RotatingFileHandler(config.APP_LOG_FILE,
                                      maxBytes = 1024*1024,
                                      backupCount = 3)
    else:
        handler = logging.StreamHandler()
    formatter = logging.Formatter(config.LOGFMT)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if config.DEBUG:
        logger.setLevel(logging.DEBUG)


config_logger()

app = create_app(config)

# Make the WSGI interface available at the top level so wfastcgi can get it.
wsgi_app = app.wsgi_app

# This is only used when running locally
if __name__ == '__main__':
    app.run()
