"""
Locano Facebook bot implementation
"""
import logging
from bot.webhook import botbp
from bot.config import init_config
from bot.translations import BotString
from bot.page import create_page


BOT_ROOT = '/bot'


def create_bot(app):
    logging.info("Creating Bot")

    init_config()

    create_page()

    # Register the Bot blueprint.
    app.register_blueprint(botbp, url_prefix=BOT_ROOT)

    logging.info("Done")
    return app
