"""
Locano Facebook bot implementation
"""
import logging
from flask import Flask
from bot.webhook import botbp
from bot.config import CONFIG

BOT_ROOT = '/bot'

def config_logger(app):
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter(CONFIG['LOGFMT'])
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if app.debug:
        logger.setLevel(logging.DEBUG)

def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)
    config_logger(app)

    logging.info("Registering App: %s", __name__)

    # Register the Bot blueprint.
    app.register_blueprint(botbp, url_prefix=BOT_ROOT)

    # Add a default root route.
    @app.route("/")
    def index():
        return "Hello GCP!"

    logging.info("Done")
    return app
