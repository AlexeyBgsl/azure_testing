import logging
import os
from flask import Flask
from logging.handlers import RotatingFileHandler
from bot import create_bot
from web import create_webaux
from config import CONFIG
from db import config as db_config

def config_logger():
    logger = logging.getLogger()
    if CONFIG['APP_LOG_FILE'] != '':
        log_dir = os.path.dirname(CONFIG['APP_LOG_FILE'])
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        handler = RotatingFileHandler(CONFIG['APP_LOG_FILE'],
                                      maxBytes = 1024*1024,
                                      backupCount = 3)
    else:
        handler = logging.StreamHandler()
    formatter = logging.Formatter(CONFIG['LOGFMT'])
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if CONFIG['DEBUG']:
        logger.setLevel(logging.DEBUG)


def create_app(config):
    app = Flask(__name__)
    app.config.from_object(CONFIG)

    logging.info("Registering App: %s", __name__)

    create_bot(app)
    create_webaux(app)

    # Add a default root route.
    @app.route("/")
    def index():
        return "Hello Azure!"

    logging.info("Done")
    return app


config_logger()

db_config(CONFIG)

app = create_app(CONFIG)

# Make the WSGI interface available at the top level so wfastcgi can get it.
wsgi_app = app.wsgi_app

# This is only used when running locally
if __name__ == '__main__':
    app.run()
