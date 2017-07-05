import logging
import functools
import fbmq
from bot.config import CONFIG

DUMP_ALL = True

def dump_mfunc(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        logging.debug("*** %s func args ***", f.__name__)
        for obj in args[1:]:
            logging.debug("Object of type %s:", type(obj))
            logging.debug(vars(obj))
        logging.debug("*** Done ***")
        return f(*args, **kwargs)
    return wrapped


def null_decorator(f):
    return f

dump_member_func = dump_mfunc if DUMP_ALL else null_decorator

class BotPage(fbmq.Page):
    def __init__(self):
        super().__init__(CONFIG['ACCESS_TOKEN'])
        self.greeting("Hi {{user_first_name}}, welcome to Locano Chatbot!")
        self.show_starting_button("Show Help")
        self.show_persistent_menu([
            fbmq.Template.ButtonPostBack('Help', 'MENU_PAYLOAD/1'),
            fbmq.Template.ButtonPostBack('Announce', 'MENU_PAYLOAD/2'),
            fbmq.Template.ButtonPostBack('Scan', 'MENU_PAYLOAD/3')])

    @dump_member_func
    def on_message(self, event):
        sender_id = event.sender_id
        message = event.message_text
        logging.debug("[U#%s] [on_message] %s", sender_id, message)
        page.send(sender_id, "thank you! your message is '%s'" % message)

    @dump_member_func
    def on_echo(self, event):
        logging.debug("[U#%s] [on_echo] %s",
                      event.sender_id,
                      event.message_text)

    @dump_member_func
    def on_delivery(self, event):
        logging.debug("[U#%s] [on_delivery] %s",
                      event.sender_id,
                      event.message_text)

    @dump_member_func
    def on_optin(self, event):
        logging.debug("[U#%s] [on_optin] %s",
                      event.sender_id,
                      event.message_text)

    @dump_member_func
    def on_read(self, event):
        logging.debug("[U#%s] [on_read] %s",
                      event.sender_id,
                      event.message_text)

    @dump_member_func
    def on_account_linking(self, event):
        logging.debug("[U#%s] [on_account_linking] %s",
                      event.sender_id,
                      event.message_text)

    @dump_member_func
    def on_after_send(self, payload, response):
        logging.debug("[U#%s] [on_after_send] %s",
                      payload.recipient.id,
                      payload.message.text)

    @dump_member_func
    def on_menu(self, payload, event):
        sender_id = event.sender_id
        item_id = payload.split('/')[1]
        logging.debug("[U#%s] [on_menu] %s", sender_id, item_id)
        page.send(sender_id, "thank you! you clicked button no. %s", item_id)


page = BotPage()


@page.callback(['MENU_PAYLOAD/(.+)'])
def click_persistent_menu(payload, event):
    page.on_menu(payload, event)


@page.handle_message
def message_handler(event):
    page.on_message(event)


@page.handle_echo
def echo_handler(event):
    page.on_echo(event)


@page.handle_delivery
def delivery_handler(event):
    page.on_delivery(event)


@page.handle_optin
def optin_handler(event):
    page.on_optin(event)


@page.handle_read
def read_handler(event):
    page.on_read(event)


@page.handle_account_linking
def postback_account_linking(event):
    page.on_account_linking(event)


@page.after_send
def after_send(payload, response):
    page.on_after_send(payload, response)
