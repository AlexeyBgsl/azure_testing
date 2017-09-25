import logging
from flask import Flask, Blueprint
from logging.handlers import RotatingFileHandler
from bot import create_bot
from ga_events import create_ga_tracker
from web import create_webaux
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


def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)

    logging.info("Registering App: %s", __name__)

    create_bot(app)
    create_webaux(app)
    create_ga_tracker(app)

    # Add a default root route.
    @app.route("/")
    def index():
        return "Hello Azure!"

    logging.info("Done")
    return app


config_logger()

app = create_app(config)

# Make the WSGI interface available at the top level so wfastcgi can get it.
wsgi_app = app.wsgi_app

# This is only used when running locally
if __name__ == '__main__':
    app.run()
