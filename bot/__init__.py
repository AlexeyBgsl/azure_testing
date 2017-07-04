"""
Locano Facebook bot implementation
"""
import logging

from flask import Flask
from bot.webhook import botbp

BOT_ROOT = '/bot'

def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)

    # Configure logging
    if app.config['DEBUG']:
        logging.basicConfig(level=logging.DEBUG)

    logging.info("Registering App: %s", __name__)

    # Register the Bot blueprint.
    app.register_blueprint(botbp, url_prefix=BOT_ROOT)

    # Add a default root route.
    @app.route("/")
    def index():
        return "Hello GCP!"

    logging.info("Done")
    return app
