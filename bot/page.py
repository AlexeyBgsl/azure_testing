import logging
import fbmq
from bot.config import CONFIG
from bot.db_datastore import Users

MENU_ID = "MENU"
HELP_ID = "HELP"
CHAN_ID = "CHANNEL"
ANNS_ID = "ANNOUNCEMENT"

HELP_MESSAGE = ("This is Locano. We help you to make and receive "
                "announcements")

DUMP_ALL = True

primitive = (int, str, bool)

def is_primitive(obj):
    return isinstance(obj, primitive)

def dump_mfunc(f):
    import functools
    @functools.wraps(f)
    def wrapped(self, *args, **kwargs):
        logging.debug("*** %s func args ***", f.__name__)
        for obj in args:
            logging.debug("Object of type %s:", type(obj))
            if is_primitive(obj):
                logging.debug(obj)
            else:
                logging.debug(vars(obj))
        logging.debug("*** Done ***")
        return f(self, *args, **kwargs)
    return wrapped


def null_decorator(f):
    return f

dump_member_func = dump_mfunc if DUMP_ALL else null_decorator

class BotPage(fbmq.Page):
    def __init__(self):
        self.users = Users()
        super().__init__(CONFIG['ACCESS_TOKEN'])
        self.greeting("Hi {{user_first_name}}, welcome to Locano Chatbot!")
        self.show_starting_button("Show Help")
        self.show_persistent_menu([
            fbmq.Template.ButtonPostBack('Channel',
                                         MENU_ID + '/' + CHAN_ID),
            fbmq.Template.ButtonPostBack('Announcement',
                                         MENU_ID + '/' + ANNS_ID),
            fbmq.Template.ButtonPostBack('Help',
                                         MENU_ID + '/' + HELP_ID),])

    def get_fb_profile(self, fbid):
        profile = self.get_user_profile(fbid)
        profile['fbid'] = fbid
        return profile

    def create_or_update_user(self, fbid):
        user = self.users.by_fbid(fbid)
        if user is None:
            user = self.users.create(self.get_fb_profile(fbid))
        return user

    @dump_member_func
    def on_message(self, event):
        sender_id = event.sender_id
        user = self.create_or_update_user(sender_id)
        if event.is_text_message:
            message = event.message_text
            logging.debug("[U#%s] [on_message] %s", sender_id, message)
            self.send(sender_id, "thank you! your message is '%s'" % message)
        else:
            self.send(sender_id, "thank you! your message received")

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
        user = self.create_or_update_user(sender_id)
        item_id = payload.split('/')[1]
        logging.debug("[U#%s] [on_menu] %s", sender_id, item_id)
        if item_id == CHAN_ID:
            pass
        elif item_id == ANNS_ID:
            pass
        else:
            self.send(sender_id, HELP_MESSAGE)


page = BotPage()


@page.callback([MENU_ID + '/(.+)'])
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
