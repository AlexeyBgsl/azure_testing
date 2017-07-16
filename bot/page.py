import logging
import fbmq
import functools
from bot.config import CONFIG
from bot.db_datastore import Users, User
from bot.chat import (
    BotChatClbTypes,
    chat_clb_handler,
    chat_menu_handler,
    BotChat
)

START_PAYLOAD = "LOCANOBOT_START"

HELP_MESSAGE = ("This is Locano. We help you to make and receive "
                "announcements")


def safe_event_seq(f):
    @functools.wraps(f)
    def wrapped(self, *args, **kwargs):
        for obj in args:
            if isinstance(obj, fbmq.Event):
                user = self.create_or_update_user(obj.sender_id)
                if user:
                    if not obj.message_seq or user.fbmsgseq < obj.message_seq:
                        result = f(self, user, *args, **kwargs)
                        if obj.message_seq:
                            user.fbmsgseq=obj.message_seq
                        user.save()
                        return result
                    else:
                        logging.error("[U#%s] incorrect event seq: %s > %d",
                                      obj.sender_id, user.fbmsgseq, obj.message_seq)
                else:
                    logging.error("[U#%s] cannot get user object", obj.sender_id)

    return wrapped


DUMP_ALL = False

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
        self.show_starting_button(START_PAYLOAD)
        self.show_persistent_menu(BotChat.get_menu_buttons())

    def _user_from_fb_profile(self, fbid):
        user = User.create(self.users, self.get_user_profile(fbid))
        user.fbid = fbid
        return user

    def create_or_update_user(self, fbid):
        user = self.users.by_fbid(fbid)
        if user is None:
            user = self._user_from_fb_profile(fbid)
        return user

    @safe_event_seq
    @dump_member_func
    def on_start(self, user, event):
        return BotChat(self, user).start(event)

    @safe_event_seq
    @dump_member_func
    def on_chat_menu(self, user, page, payload, event):
        return chat_menu_handler(user, page, payload, event)

    @safe_event_seq
    @dump_member_func
    def on_chat_callback(self, user, page, payload, event):
        return chat_clb_handler(user, page, payload, event)

    @safe_event_seq
    @dump_member_func
    def on_message(self, user, event):
        sender_id = event.sender_id
        if event.is_quick_reply:
            logging.debug("[U#%s] [on_message] ignored as a quick reply", sender_id)
        elif event.is_text_message:
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


page = BotPage()


@page.callback([BotChatClbTypes['ClbMenu'] + '/(.+)'])
def menu_handler(payload, event):
    page.on_chat_menu(page, payload, event)


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


@page.callback([BotChatClbTypes['ClbQRep'] + '/(.+)'])
def chat_callback_handler(payload, event):
    page.on_chat_callback(page, payload, event)

@page.callback([START_PAYLOAD])
def start_callback(payload, event):
    page.on_start(event)