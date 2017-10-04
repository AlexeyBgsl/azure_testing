import logging
import fbmq
import functools
from bot.config import CONFIG
from db import User, DCRS, UpdateOps
from bot.chat import (
    BotChatClbTypes,
    chat_clb_handler,
    chat_menu_handler,
    chat_msg_handler,
    BotChat
)
from bot.translations import BotString

START_PAYLOAD = "LOCANOBOT_START"


DUMP_ALL = False

primitive = (int, str, bool)


def is_primitive(obj):
    return isinstance(obj, primitive)


def dump_mfunc(f):
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
    singleton = None

    def __init__(self):
        super().__init__(CONFIG['ACCESS_TOKEN'])
        self.greeting(str(BotString('SID_GREETING')))
        self.show_starting_button(START_PAYLOAD)
        self.show_persistent_menu(BotChat.get_menu_buttons())

    def _user_from_fb_profile(self, fbid):
        return DCRS.Users.create(fbid=fbid,
                                 fb_profile=self.get_user_profile(fbid))

    def _check_message_seq(self, user, event):
        message_seq = event.message_seq
        if message_seq and user.fbmsgseq >= message_seq:
            logging.warning("[U#%s] incorrect event seq: %s >= %d",
                            user.fbid, user.fbmsgseq, message_seq)
            return False

        user.update(UpdateOps.Supported.SET, fbmsgseq=message_seq)
        return True

    def create_or_update_user(self, fbid):
        user = DCRS.Users.find_unique(fbid=fbid)
        if user is None:
            user = self._user_from_fb_profile(fbid)
        return user

    @dump_member_func
    def on_start(self, event):
        user = self.create_or_update_user(event.sender_id)
        return BotChat(self, user).start(event)

    @dump_member_func
    def on_chat_menu(self, page, payload, event):
        user = self.create_or_update_user(event.sender_id)
        return chat_menu_handler(user, page, payload, event)

    @dump_member_func
    def on_chat_callback(self, page, payload, event):
        user = self.create_or_update_user(event.sender_id)
        return chat_clb_handler(user, page, payload, event)

    @dump_member_func
    def on_message(self, event):
        sender_id = event.sender_id
        user = self.create_or_update_user(sender_id)
        if not user:
            logging.error("[U#%s] [on_message] cannot get user",
                          sender_id)
        elif not self._check_message_seq(user, event):
            logging.debug("[U#%s] [on_message] ignored due to incorrect seq",
                          sender_id)
        elif event.is_quick_reply:
            logging.debug("[U#%s] [on_message] ignored as a quick reply",
                          sender_id)
        else:
            chat_msg_handler(user, get_page(), event)

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
    def on_referral(self, event):
        sender_id = event.sender_id
        user = self.create_or_update_user(sender_id)
        if not user:
            logging.error("[U#%s] [on_message] cannot get user",
                          sender_id)
        else:
            return BotChat(self, user).on_referral(event)

    @dump_member_func
    def on_after_send(self, payload, response):
        logging.debug("[U#%s] [on_after_send] %s",
                      payload.recipient.id,
                      payload.message.text)


def get_page():
    return BotPage.singleton


def create_page():
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

    @page.handle_referral
    def referral_callback(event):
        page.on_referral(event)

    @page.after_send
    def after_send(payload, response):
        page.on_after_send(payload, response)

    @page.callback([BotChatClbTypes['ClbQRep'] + '/(.+)'])
    def chat_callback_handler(payload, event):
        page.on_chat_callback(page, payload, event)

    @page.callback([START_PAYLOAD])
    def start_callback(payload, event):
        page.on_start(event)

    BotPage.singleton = page
    return page