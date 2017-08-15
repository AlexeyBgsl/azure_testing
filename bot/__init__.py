"""
Locano Facebook bot implementation
"""
import logging
from flask import Flask
from bot.webhook import botbp
from bot.config import CONFIG, set_env
from bot.translations import BotString
from bot.page import create_page


BOT_ROOT = '/bot'


def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)

    logging.info("Registering App: %s", __name__)

    set_env(is_production=config.PRODUCTION_APP_ENV)

    create_page()

    # Register the Bot blueprint.
    app.register_blueprint(botbp, url_prefix=BOT_ROOT)

    # Add a default root route.
    @app.route("/")
    def index():
        return "Hello GCP!"

    logging.info("Done")
    return app
