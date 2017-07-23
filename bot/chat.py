import logging
from abc import ABC
from fbmq import QuickReply, Template
from bot.translations import BotString
from bot.db_datastore import Channel


BotChatClbTypes = dict(
    ClbQRep="CHAT_CLB_QREP",
    ClbMenu="CHAT_CLB_MENU",
    ClbMsg="CHAT_CLB_MSG"
)


class Payload(object):
    DELIMITER='/'

    @classmethod
    def from_string(cls, payload):
        params = payload.split(cls.DELIMITER)

        for k, v in BotChatClbTypes.items():
            if params[0] == v:
                return cls(k, params[1], params[2])

        return None

    def __init__(self, type, class_name, action_id):
        if not class_name or not type or not action_id:
            raise ValueError(
                "{}: all fields are mandatory".format(self.__name__))
        self.class_name = class_name
        self.type = type
        self.action_id = action_id

    def __str__(self):
        return BotChatClbTypes[self.type] + self.DELIMITER + \
               self.class_name + self.DELIMITER + self.action_id


class ClassCollection(object):
    def __init__(self):
        self.subs = {}

    def register(self, scls):
        self.subs[scls.__name__] = scls
        return scls

    def cls(self, class_name):
        return self.subs[class_name] if class_name in self.subs else None

    def instantiate(self, class_name, *args, **kwargs):
        scls = self.cls(class_name)
        return scls(*args, **kwargs) if scls else None


class CallToAction(object):
    def __init__(self, title_sid, class_name, action_id=None):
        self.title_sid = title_sid
        self.class_name = class_name
        self.action_id = action_id if action_id else class_name

    @property
    def title(self):
        return str(BotString(self.title_sid))


class NoCallToAction(CallToAction):
    CLS_NAME = 'IdleChatState'

    def __init__(self, title_sid):
        super().__init__(title_sid, self.CLS_NAME)


class BasicChatState(ABC):
    QREP_CTA = []
    MSG_STR_ID = None

    @classmethod
    def class_name(cls):
        return cls.__name__

    def _prepare_qreps(self):
        if not self.QREP_CTA:
            return None
        qreps = []
        for cta in self.QREP_CTA:
            p = Payload('ClbQRep', self.class_name(), cta.action_id)
            qreps.append(QuickReply(cta.title, str(p)))
        return qreps

    def _send(self, fbid, message, metadata = None):
        qreps = self._prepare_qreps()
        self.page.send(fbid, message, quick_replies=qreps, metadata=metadata)

    def _register_for_user_input(self, action_id):
        p = Payload('ClbMsg', self.class_name(), action_id)
        self.page.register_for_message(self.user, str(p))

    def __init__(self, page, user):
        self.page = page
        self.user = user

    def get_message(self):
        message = str(BotString(self.MSG_STR_ID)) if self.MSG_STR_ID else None
        return message, None

    def show(self):
        message, metadata = self.get_message()
        if message:
            self._send(self.user.fbid, message, metadata)

    def on_user_input(self, action_id, event):
        return None

    def on_action(self, type, action_id, event):
        logging.debug("%s: on_action(%s): %s arrived",
                      self.class_name(), type, action_id)
        if type == 'ClbQRep':
            for cta in self.QREP_CTA:
                if cta.action_id == action_id:
                    logging.debug("%s: next CTA: %s",
                                  self.class_name(), cta.class_name)
                    return cta.class_name
        elif type == 'ClbMsg':
            return self.on_user_input(action_id, event)
        else:
            logging.warning("%s: on_action(%s): unknown type",
                            self.class_name(), type)

        return None


step_collection = ClassCollection()


@step_collection.register
class RootChatState(BasicChatState):
    QREP_CTA = [
        CallToAction('SID_BROWSE_CHANNELS', 'BrowseChannelsChatState'),
        CallToAction('SID_MY_CHANNELS', 'MyChannelsChatState'),
        NoCallToAction('SID_MAKE_ANNOUNCEMENT'),
    ]
    MSG_STR_ID = 'SID_ROOT_PROMPT'


@step_collection.register
class IdleChatState(BasicChatState):
    MSG_STR_ID = 'SID_DBG_NO_ACTION'


@step_collection.register
class RootChannelsChatState(BasicChatState):
    QREP_CTA = [
        CallToAction('SID_BROWSE_CHANNELS', 'BrowseChannelsChatState'),
        CallToAction('SID_MY_CHANNELS', 'MyChannelsChatState'),
        CallToAction('SID_CHANNELS_HELP',  'ChannelsHelpChatState'),
    ]
    MSG_STR_ID = 'SID_CHANNELS_PROMPT'


@step_collection.register
class ChannelsHelpChatState(BasicChatState):
    QREP_CTA = [
        NoCallToAction('SID_HELP_CHANNEL_DETAILS'),
        NoCallToAction('SID_HELP_CHANNEL_EXAMPLES')
    ]
    MSG_STR_ID = 'SID_HELP_CHANNELS_PROMPT'


@step_collection.register
class BrowseChannelsChatState(BasicChatState):
    QREP_CTA = [
        NoCallToAction('SID_BROWSE_NEWS_CHANNELS'),
        NoCallToAction('SID_BROWSE_ENTERTAINMENT_CHANNELS'),
        NoCallToAction('SID_BROWSE_SPORT_CHANNELS'),
        NoCallToAction('SID_BROWSE_CULTURE_CHANNELS'),
        NoCallToAction('SID_BROWSE_LOCAL_CHANNELS'),
    ]
    MSG_STR_ID = 'SID_BROWSE_CHANNELS_PROMPT'


@step_collection.register
class MyChannelsChatState(BasicChatState):
    QREP_CTA = [
        CallToAction('SID_CREATE_CHANNEL', 'CreateChannelsChatState'),
        NoCallToAction('SID_EDIT_CHANNEL'),
        NoCallToAction('SID_LIST_MY_CHANNELS'),
    ]
    MSG_STR_ID = 'SID_MY_CHANNELS_PROMPT'


@step_collection.register
class CreateChannelsChatState(BasicChatState):
    MSG_STR_ID = 'SID_GET_CHANNEL_NAME'

    def show(self):
        message, metadata = self.get_message()
        if message:
            self._register_for_user_input('SID_GET_CHANNEL_NAME')
            self._send(self.user.fbid, message, metadata)

    def create_channel(self, name):
        c = Channel()
        c.name = name
        c.owner_uid = self.user.oid
        c.save()
        return c

    def on_user_input(self, action_id, event):
        logging.debug("[U#%s] on_user_input arrived: %s",
                      event.sender_id, action_id)
        if action_id == 'SID_GET_CHANNEL_NAME':
            if event.is_text_message:
                logging.debug("[U#%s] Desired channel name is: %s",
                              event.sender_id, event.message_text)
                c = self.create_channel(event.message_text)
                self._register_for_user_input(str(c.chid))
                s = str(BotString('SID_GET_CHANNEL_DESC'))
                self._send(self.user.fbid, s.format(channel_name=c.name,
                                                    channel_id=c.str_chid))
            else:
                self.show()
        else:
            if event.is_text_message:
                c = Channel.by_chid(action_id)
                logging.debug("[U#%s] Desired %s channel desc is: %s",
                              event.sender_id, c.str_chid, event.message_text)
                c.desc = event.message_text
                c.save()
                s = str(BotString('SID_CHANNEL_CREATED'))
                self._send(self.user.fbid, s.format(channel_name=c.name,
                                                    channel_id=c.str_chid))
                return 'IdleChatState'

        return None


class BotChat(object):
    MENU_CTA = [
        NoCallToAction('SID_MENU_ANNOUNCEMENTS'),
        CallToAction('SID_MENU_CHANNELS', 'RootChannelsChatState'),
        CallToAction('SID_MENU_HELP', 'RootHelpChatState'),
    ]

    @classmethod
    def class_name(cls):
        return cls.__name__

    @classmethod
    def clb_by_payload(cls, user, page, payload, event):
        logging.debug("[U#%s] clb arrived: %s",
                      event.sender_id, payload)
        p = Payload.from_string(payload)
        if p:
            cls(page, user, scls_name=p.class_name).on_action(p.type,
                                                              p.action_id,
                                                              event)
        else:
            logging.warning("[U#%s] clb: bad payload: %s",
                            event.sender_id, payload)

    @classmethod
    def get_menu_buttons(cls):
        buttons = []
        for cta in cls.MENU_CTA:
            p = Payload('ClbMenu', cls.class_name(), cta.action_id)
            buttons.append(Template.ButtonPostBack(cta.title, str(p)))
        return buttons

    def _on_menu(self, action_id, event):
        for cta in self.MENU_CTA:
            if cta.action_id == action_id:
                logging.debug("%s: next CTA: %s",
                              self.class_name(), cta.class_name)
                return cta.class_name

    def __init__(self, page, user, scls_name=None):
        self.page = page
        self.user = user
        self.instantiate_state(scls_name if scls_name else 'RootChatState')

    def instantiate_state(self, class_name):
        self.state = step_collection.instantiate(class_name,
                                                 self.page,
                                                 self.user)

    def start(self, event):
        self.state.show()

    def on_action(self, type, action_id, event):
        logging.debug("%s: on_action(%s): %s arrived",
                      self.class_name(), type, action_id)
        if type == 'ClbMenu':
            next_state = self._on_menu(action_id, event)
        else:
            next_state = self.state.on_action(type, action_id, event)
        if next_state:
            self.instantiate_state(next_state)
            self.state.show()


def chat_clb_handler(user, page, payload, event):
    logging.debug("[U#%s] Clb Handler: %s", event.sender_id, payload)
    BotChat.clb_by_payload(user, page, payload, event)


def chat_menu_handler(user, page, payload, event):
    logging.debug("[U#%s] Menu Handler: %s", event.sender_id, payload)
    BotChat.clb_by_payload(user, page, payload, event)


def chat_msg_handler(user, page, payload, event):
    logging.debug("[U#%s] Msg Handler: %s", event.sender_id, payload)
    BotChat.clb_by_payload(user, page, payload, event)
