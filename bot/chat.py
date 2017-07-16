import logging
from abc import ABC, abstractmethod
from fbmq import QuickReply, Template

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
    def __init__(self, title, action_id, class_name):
        self.title = title
        self.action_id = action_id
        self.class_name = class_name


class NoCallToAction(CallToAction):
    CLS_NAME = 'IdleChatState'
    ACTION_ID = 'CTANoActionID'

    def __init__(self, title):
        super().__init__(title, self.ACTION_ID, self.CLS_NAME)


class BasicChatState(ABC):
    MENU_CTA = []
    QREP_CTA = []

    @classmethod
    def class_name(cls):
        return cls.__name__

    def _prepare_qreps(self):
        qreps = []
        for cta in self.QREP_CTA:
            p = Payload('ClbQRep', self.class_name(), cta.action_id)
            qreps.append(QuickReply(cta.title, str(p)))
        return qreps

    def _show_menu(self):
        if len(self.MENU_CTA):
            buttons = []
            for cta in self.MENU_CTA:
                p = Payload('ClbMenu', self.class_name(), cta.action_id)
                buttons.append(Template.ButtonPostBack(cta.title, str(p)))
            self.page.show_persistent_menu(buttons)
        else:
            self.page.hide_persistent_menu()

    def _send(self, fbid, message, metadata = None):
        qreps = self._prepare_qreps()
        self.page.send(fbid, message, quick_replies=qreps, metadata=metadata)

    def __init__(self, page):
        self.page = page

    def get_message(self):
        return None, None

    def show(self, fbid=None):
        self._show_menu()
        if fbid:
            message, metadata = self.get_message()
            if message:
                self._send(fbid, message, metadata)

    def on_action_done(self, cta, event):
        pass

    def on_action(self, type, action_id, event):
        logging.debug("%s: on_action(%s): %s arrived",
                      self.class_name(), type, action_id)
        if type == 'ClbQRep':
            ctas = self.QREP_CTA
        elif type == 'ClbMenu':
            ctas = self.MENU_CTA
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
    MENU_CTA = [
        CallToAction('Channels', 'RtChls', 'FirstChannelsChatState'),
        CallToAction('Announcements', 'RtAnns', 'FirstAnnouncementsChatState'),
        CallToAction('Help', 'RtHelp', 'FirstHelpChatState'),
    ]
    QREP_CTA = MENU_CTA

    def get_message(self):
        return 'What do you want to do next?', None


@step_collection.register
class IdleChatState(RootChatState):
    pass


@step_collection.register
class FirstChannelsChatState(BasicChatState):
    MENU_CTA = [
        NoCallToAction('List My Channels'),
        NoCallToAction('Subscribe'),
        NoCallToAction('Unsubscribe')
    ]
    QREP_CTA = MENU_CTA

    def get_message(self):
        return 'What do you want to do next?', None


@step_collection.register
class FirstAnnouncementsChatState(BasicChatState):
    pass


class BotChat(object):
    @classmethod
    def clb_by_payload(cls, page, payload, event):
        logging.debug("[U#%s] clb arrived: %s",
                      event.sender_id, payload)
        p = Payload.from_string(payload)
        if p:
            cls(page, scls_name=p.class_name).on_action(p.type,
                                                        p.action_id,
                                                        event)
        else:
            logging.warning("[U#%s] clb: bad payload: %s",
                            event.sender_id, payload)

    def __init__(self, page, scls_name=None):
        self.page = page
        self.instantiate_state(scls_name if scls_name else 'RootChatState')

    def instantiate_state(self, class_name):
        self.state = step_collection.instantiate(class_name, self.page)

    def start(self):
        self.state.show()

    def on_action(self, type, action_id, event):
        next_state = self.state.on_action(type, action_id, event)
        if next_state:
            self.instantiate_state(next_state)
            self.state.show(event.sender_id)


def chat_clb_handler(user, page, payload, event):
    logging.debug("[U#%s] Clb Handler: %s", event.sender_id, payload)
    BotChat.clb_by_payload(page, payload, event)


def chat_menu_handler(user, page, payload, event):
    logging.debug("[U#%s] Menu Handler: %s", event.sender_id, payload)
    BotChat.clb_by_payload(page, payload, event)
