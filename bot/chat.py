import logging
from abc import ABC, abstractmethod
from fbmq import QuickReply, Template
from bot.translations import StringId, BotString

CHAT_CLB_ID = 'CHAT_CLB'
CHAT_MENU_ID = 'CHAT_MENU'
START_ACTION = 'Start'


BotChatClbTypes = dict(
    ClbQRep="CHAT_CLB_QREP",
    ClbMenu="CHAT_CLB_MENU"
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

    def on_action_done(self, cta, event):
        pass

    def on_action(self, type, action_id, event):
        logging.debug("%s: on_action(%s): %s arrived",
                      self.class_name(), type, action_id)
        if type == 'ClbQRep':
            ctas = self.QREP_CTA
        else:
            logging.warning("%s: on_action(%s): unknown type",
                            self.class_name(), type)
            ctas = None

        if ctas:
            for cta in ctas:
                if cta.action_id == action_id:
                    self.on_action_done(cta, event)
                    logging.debug("%s: next CTA: %s",
                                  self.class_name(), cta.class_name)
                    return cta.class_name
        return None


step_collection = ClassCollection()


@step_collection.register
class RootChatState(BasicChatState):
    QREP_CTA = [
        CallToAction(StringId.SID_MENU_CHANNELS,
                     'FirstChannelsChatState'),
        CallToAction(StringId.SID_MENU_ANNOUNCEMENTS,
                     'FirstAnnouncementsChatState'),
        CallToAction(StringId.SID_MENU_HELP,
                     'FirstHelpChatState'),
    ]
    MSG_STR_ID = StringId.SID_SELECT_ACTION


@step_collection.register
class IdleChatState(RootChatState):
    pass


@step_collection.register
class FirstChannelsChatState(BasicChatState):
    QREP_CTA = [
        NoCallToAction(StringId.SID_LIST_MY_CHANNELS),
        NoCallToAction(StringId.SID_SUBSCRIBE),
        NoCallToAction(StringId.SID_UNSUBSCRIBE)
    ]
    MSG_STR_ID = StringId.SID_SELECT_ACTION


@step_collection.register
class FirstAnnouncementsChatState(BasicChatState):
    pass


class BotChat(object):
    MENU_CTA = [
        CallToAction(StringId.SID_MENU_ANNOUNCEMENTS,
                     'FirstAnnouncementsChatState'),
        CallToAction(StringId.SID_MENU_CHANNELS,
                     'FirstChannelsChatState'),
        CallToAction(StringId.SID_MENU_HELP,
                     'FirstHelpChatState'),
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
