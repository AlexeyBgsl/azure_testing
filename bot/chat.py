import logging
import re
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

    def title(self, user=None):
        return str(BotString(self.title_sid, user=user))


class NoCallToAction(CallToAction):
    CLS_NAME = 'IdleChatState'

    def __init__(self, title_sid):
        super().__init__(title_sid, self.CLS_NAME)


class HandlerResult():
    def __init__(self, next_cls_name, **kwargs):
        self.next_cls_name = next_cls_name
        self.extra_args = kwargs


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
            qreps.append(QuickReply(cta.title(self.user), str(p)))
        return qreps

    def send(self, sid, channel=None, with_qreps=False):
        qreps = self._prepare_qreps() if with_qreps else None
        message = self.get_message(sid, channel=channel)
        self.page.send(self.user.fbid, message, quick_replies=qreps)

    def _register_for_user_input(self, action_id):
        p = Payload('ClbMsg', self.class_name(), action_id)
        self.page.register_for_message(self.user, str(p))

    def __init__(self, page, user, **kwargs):
        self.page = page
        self.user = user
        self.extra_params = kwargs

    def get_message(self, sid=MSG_STR_ID, channel=None):
        return str(BotString(sid, user=self.user, channel=channel))

    def show(self, channel=None):
        if self.MSG_STR_ID:
            self.send(self.MSG_STR_ID, channel=channel, with_qreps=True)

    def reinstantiate(self, channel=None):
        c = None
        if channel:
            if isinstance(channel, Channel):
                c = channel
            elif isinstance(channel, str):
                c = Channel.by_chid(channel)
            elif isinstance(channel, int):
                c = Channel.by_chid(channel)
        self.send('SID_DONT_UNDERSTAND', channel=c, with_qreps=False)
        return HandlerResult(self.class_name(),
                             chid=c.oid if c else None)

    def on_user_input(self, action_id, event):
        return None

    def on_quick_response(self, action_id, event):
        for cta in self.QREP_CTA:
            if cta.action_id == action_id:
                logging.debug("%s: next CTA: %s",
                              self.class_name(), cta.class_name)
                return HandlerResult(cta.class_name)
        return None

    def on_action(self, type, action_id, event):
        logging.debug("%s: on_action(%s): %s arrived",
                      self.class_name(), type, action_id)
        if type == 'ClbQRep':
            return self.on_quick_response(action_id, event)
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
        CallToAction('SID_EDIT_CHANNEL', 'EditChannelRootChatState'),
        NoCallToAction('SID_LIST_MY_CHANNELS'),
    ]
    MSG_STR_ID = 'SID_MY_CHANNELS_PROMPT'


@step_collection.register
class CreateChannelsChatState(BasicChatState):
    MSG_STR_ID = 'SID_GET_CHANNEL_NAME'

    def show(self):
        assert self.MSG_STR_ID
        self._register_for_user_input('SID_GET_CHANNEL_NAME')
        super().show()

    def create_channel(self, name):
        c = Channel(name=name, owner_uid=self.user.oid)
        c.save()
        return c

    def on_user_input(self, action_id, event):
        logging.debug("[U#%s] on_user_input arrived: %s",
                      event.sender_id, action_id)
        assert action_id == 'SID_GET_CHANNEL_NAME'
        if event.is_text_message:
            logging.debug("[U#%s] Desired channel name is: %s",
                          event.sender_id, event.message_text)
            c = self.create_channel(event.message_text)
            return HandlerResult('GetChannelDescChatState', chid=c.chid)

        return self.reinstantiate(action_id)


@step_collection.register
class GetChannelDescChatState(BasicChatState):
    MSG_STR_ID = 'SID_GET_CHANNEL_DESC'

    def show(self):
        chid = self.extra_params['chid']
        self._register_for_user_input(str(chid))
        super().show(channel=Channel.by_chid(chid))

    def on_user_input(self, action_id, event):
        logging.debug("[U#%s] on_user_input arrived: %s",
                      event.sender_id, action_id)
        if event.is_text_message:
            c = Channel.by_chid(action_id)
            logging.debug("[U#%s] Desired %s channel desc is: %s",
                          event.sender_id, c.str_chid, event.message_text)
            c.desc = event.message_text
            c.save()
            return HandlerResult('ChannelCreationDoneChatState',
                                 chid=action_id)

        return self.reinstantiate(action_id)

@step_collection.register
class ChannelCreationDoneChatState(BasicChatState):
    MSG_STR_ID = 'SID_CHANNEL_CREATED'

    def show(self):
        chid = self.extra_params['chid']
        super().show(channel=Channel.by_chid(chid))


@step_collection.register
class EditChannelRootChatState(BasicChatState):
    MSG_STR_ID = 'SID_SELECT_CHANNEL_PROMPT'

    def on_selection(self, chid):
        c = Channel.by_chid(chid)
        if c:
            return HandlerResult('EditChannelTypeChatState', chid=chid)
        return HandlerResult(self.class_name())

    def _prepare_qreps(self):
        ch_list = Channel.by_owner_uid(self.user.oid)
        qreps = []
        for e in ch_list:
            c = Channel(entity=e)
            p = Payload('ClbQRep', self.class_name(), str(c.oid))
            qreps.append(QuickReply(c.name, str(p)))
        return qreps

    def show(self):
        self._register_for_user_input('SID_CHANNEL_ID')
        super().show()

    def on_quick_response(self, action_id, event):
        return self.on_selection(action_id)

    def on_user_input(self, action_id, event):
        logging.debug("[U#%s] on_user_input arrived: %s",
                      event.sender_id, action_id)
        if event.is_text_message:
            chid = re.sub(r"\s+", "", event.message_text, flags=re.UNICODE)
            chid = re.sub(r"-", "", chid)
            return self.on_selection(chid)

        return self.reinstantiate()


@step_collection.register
class EditChannelTypeChatState(BasicChatState):
    QREP_CTA = [
        NoCallToAction('SID_EDIT_CHANNEL_NAME'),
        NoCallToAction('SID_EDIT_CHANNEL_DESC'),
        NoCallToAction('SID_EDIT_CHANNEL_DELETE'),
    ]
    MSG_STR_ID = 'SID_SELECT_CHANNEL_EDIT_ACTION'

    def show(self):
        chid = self.extra_params['chid']
        super().show(channel=Channel.by_chid(chid))


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
            buttons.append(Template.ButtonPostBack(cta.title(), str(p)))
        return buttons

    def _on_menu(self, action_id, event):
        for cta in self.MENU_CTA:
            if cta.action_id == action_id:
                logging.debug("%s: next CTA: %s",
                              self.class_name(), cta.class_name)
                return HandlerResult(cta.class_name)
        return None

    def __init__(self, page, user, scls_name=None):
        self.page = page
        self.user = user
        if not scls_name:
            scls_name = 'RootChatState'
        self.instantiate_state(HandlerResult(scls_name))

    def instantiate_state(self, result):
        self.state = step_collection.instantiate(result.next_cls_name,
                                                 self.page,
                                                 self.user,
                                                 **result.extra_args)

    def start(self, event):
        self.state.show()

    def on_action(self, type, action_id, event):
        logging.debug("%s: on_action(%s): %s arrived",
                      self.class_name(), type, action_id)
        if type == 'ClbMenu':
            result = self._on_menu(action_id, event)
        else:
            result = self.state.on_action(type, action_id, event)
        if result:
            self.instantiate_state(result)
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
