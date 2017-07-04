import fbmq
from bot.config import CONFIG

page = fbmq.Page(CONFIG['ACCESS_TOKEN'])

@page.handle_message
def message_handler(event):
    """:type event: fbmq.Event"""
    sender_id = event.sender_id
    message = event.message_text

    page.send(sender_id, "thank you! your message is '%s'" % message)


@page.after_send
def after_send(payload, response):
    """:type payload: fbmq.Payload"""
    print("complete")
