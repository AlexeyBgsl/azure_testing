import logging

from flask import Blueprint, request

from bot.config import is_correct_token
from bot.page import get_page

botbp = Blueprint('botbp', __name__)


@botbp.route('/', methods=['GET'])
def verify():
    """Verification handler"""
    logging.info("Handling verification")
    if (request.args.get('hub.mode', '') == 'subscribe' and
            is_correct_token(request.args.get('hub.verify_token', ''))):
        return request.args.get('hub.challenge', '')
    else:
        return "Invalid verification token"


@botbp.route('/', methods=['POST'])
def handle_messages():
    """ FB Webhook handler """
    logging.info("Handling webhook")
    get_page().handle_webhook(request.get_data(as_text=True))
    return "ok"
