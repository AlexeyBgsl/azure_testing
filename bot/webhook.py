import logging
import json
import requests

from flask import Blueprint, request

ACCESS_TOKEN = 'EAAUEkHk0iswBAMq2jCxGo9BxX5z5wdo74oUF64ZC0Lim6rP6BAOgCwwDoJ2wtYBD7Vrw6ZBfUgweLacbgwv8zUJa6agoOb8aSnyLzA6GkZAYVY5dprNt0QXfZA0GjKOZBGBZBGmz4OnSOmWboNbrwZBg79kpmY5MPmgPw1RMVfT40D8xdu5FZBmt'
VERIFY_TOKEN = 'loc@no'
FB_API_POINT = 'https://graph.facebook.com/v2.9/me/messages'

botbp = Blueprint('botbp', __name__)


def send_message(user_id, text):
    """Send the message text to user
    """
    data = {
        "recipient": {"id": user_id},
        "message": {"text": text}
    }
    resp = requests.post(FB_API_POINT,
                         params={"access_token": ACCESS_TOKEN},
                         json=data)
    logging.info(resp.content)


def messaging_events(payload):
    """Generate tuples of (sender_id, message_text) from the provided payload.
    """
    data = json.loads(payload)
    events = data["entry"][0]["messaging"]
    for event in events:
        if "message" in event and "text" in event["message"]:
            yield event["sender"]["id"], event["message"]["text"].encode('unicode_escape')
        else:
            yield event["sender"]["id"], "UNKNOWN"

@botbp.route('/', methods=['GET'])
def handle_verification():
    """Handles verification"""
    logging.info("Handling verification")
    if request.args['hub.verify_token'] == VERIFY_TOKEN:
        return request.args['hub.challenge']
    else:
        return "Invalid verification token"


@botbp.route('/', methods=['POST'])
def handle_messages():
    """Handles messages from API"""
    logging.info("Handling Messages")
    payload = request.get_data()
    logging.info("Payload: %s", payload)
    for sender, message in messaging_events(payload):
        logging.info("Incoming from %s: %s", sender, message)
        send_message(sender, message)
    return "ok"
