import logging
from abc import ABC
from fbmq import QuickReply, Template
from bot.translations import BotString
from db import Channel, Annc
from bot.horn import Horn


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
            if params[0] == v and len(params) > 2:
                param = params[3] if len(params) > 3 else None
                return cls(k, params[1], params[2], param)

        return None

    def __init__(self, type, class_name, action_id, param=None):
        if not class_name or not type or not action_id:
            raise ValueError(
                "{}: all fields are mandatory".format(self.__name__))
        self.class_name = class_name
        self.type = type
        self.action_id = action_id
        self.param = param

    def __str__(self):
        s = BotChatClbTypes[self.type] + self.DELIMITER + \
            self.class_name + self.DELIMITER + self.action_id
        if self.param:
            s = s + self.DELIMITER + self.param
        return s


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
    CLS_NAME = 'NotImplementedChatState'

    def __init__(self, title_sid):
        super().__init__(title_sid, self.CLS_NAME)


class HandlerResult():
    def __init__(self, next_cls_name, **kwargs):
        self.next_cls_name = next_cls_name
        self.extra_args = kwargs


class BasicChatState(ABC):
    QREP_CTA = []
    MSG_STR_ID = None
    USER_INPUT = False

    @classmethod
    def class_name(cls):
        return cls.__name__

    def payload(self, type, action_id):
        p = Payload(type, self.class_name(), action_id, param=self._to_param())
        return str(p)

    @property
    def _channel(self):
        return Channel.by_oid(self.chid) if self.chid else None

    @property
    def _announcement(self):
        return Annc.by_oid(self.aid) if self.aid else None

    def _prepare_qreps(self):
        if not self.QREP_CTA:
            return None
        qreps = []
        for cta in self.QREP_CTA:
            p = self.payload('ClbQRep', cta.action_id)
            qreps.append(QuickReply(cta.title(self.user), p))
        return qreps

    def _send(self, sid, with_qreps=False):
        qreps = None
        if with_qreps:
            qreps = self._prepare_qreps()
            if qreps and not len(qreps):
                logging.warning("%s: empty QREPS generated", self.class_name())
                qreps = None
        message = str(BotString(sid, user=self.user, channel=self._channel))
        self.page.send(self.user.fbid, message, quick_replies=qreps)

    def _to_param(self):
        if self.aid:
            return 'A' + self.aid
        if self.chid:
            return 'C' + self.chid
        return None

    def _from_param(self, param):
        if param:
            if param[0] == 'A':
                self.aid = param[1:]
                self.chid = self._announcement.chid
            elif param[0] == 'C':
                self.chid = param[1:]

    def _register_for_user_input(self):
        p = self.payload('ClbMsg', 'UsrInput')
        self.page.register_for_message(self.user, p)

    def __init__(self, page, user, chid=None, aid=None):
        self.page = page
        self.user = user
        if aid:
            self.aid = aid
            self.chid = self._announcement.chid
        else:
            self.aid = None
            self.chid = chid

    def _get_show_sid(self):
        return self.MSG_STR_ID

    def show(self):
        if self.USER_INPUT:
            self._register_for_user_input()
        sid = self._get_show_sid()
        if sid:
            self._send(sid, with_qreps=True)

    def done(self, sid):
        self._send(sid=sid)
        return HandlerResult('IdleChatState')

    def reinstantiate(self):
        self._send('SID_DONT_UNDERSTAND', with_qreps=False)
        return HandlerResult(self.class_name(), chid=self.chid)

    def on_user_input(self, event):
        return None

    def on_quick_response(self, action_id, event):
        for cta in self.QREP_CTA:
            if cta.action_id == action_id:
                logging.debug("%s: next CTA: %s",
                              self.class_name(), cta.class_name)
                return HandlerResult(cta.class_name, chid=self.chid)
        return None

    def on_action(self, type, action_id, param, event):
        self._from_param(param)
        logging.debug("%s: on_action(%s): %s arrived",
                      self.class_name(), type, action_id)
        if type == 'ClbQRep':
            logging.debug("[U#%s] on_quick_response(%s)",
                          event.sender_id, action_id)
            return self.on_quick_response(action_id, event)
        elif type == 'ClbMsg':
            assert action_id == 'UsrInput'
            logging.debug("[U#%s] on_user_input(%s)",
                          event.sender_id,
                          event.message_text if event.is_text_message else '')
            return self.on_user_input(event)
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
        CallToAction('SID_MY_SUBSCRIPTIONS', 'RootSubscriptionsChatState'),
        CallToAction('SID_MAKE_ANNOUNCEMENT', 'MakeAnncChatState'),
    ]
    MSG_STR_ID = 'SID_ROOT_PROMPT'


@step_collection.register
class IdleChatState(RootChatState):
    MSG_STR_ID = 'SID_IDLE_PROMPT'


@step_collection.register
class NotImplementedChatState(RootChatState):
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
    ]
    MSG_STR_ID = 'SID_MY_CHANNELS_PROMPT'


@step_collection.register
class CreateChannelsChatState(BasicChatState):
    MSG_STR_ID = 'SID_GET_CHANNEL_NAME'
    USER_INPUT = True

    def create_channel(self, name):
        c = Channel.create(name=name, owner_uid=self.user.oid)
        r = BotRef(sub=c.uchid)
        mc = self.page.get_messenger_code(ref=r.ref)
        c.set_code(ref=r.ref, messenger_code_url=mc)
        return c

    def on_user_input(self, event):
        if event.is_text_message:
            logging.debug("[U#%s] Desired channel name is: %s",
                          event.sender_id, event.message_text)
            c = self.create_channel(event.message_text)
            return HandlerResult('GetChannelDescChatState', chid=str(c.oid))

        return self.reinstantiate()


@step_collection.register
class GetChannelDescChatState(BasicChatState):
    MSG_STR_ID = 'SID_GET_CHANNEL_DESC'
    USER_INPUT = True

    def on_user_input(self, event):
        assert self.chid
        if event.is_text_message:
            c = self._channel
            logging.debug("[U#%s] Desired %s channel desc is: %s",
                          event.sender_id, c.oid, event.message_text)
            c.desc = event.message_text
            c.save()
            return self.done('SID_CHANNEL_CREATED')

        return self.reinstantiate()


class SelectChannelChatState(BasicChatState):
    MSG_STR_ID = 'SID_SELECT_CHANNEL_PROMPT'
    USER_INPUT = True
    NEXT_CLS_NAME = None

    def _prepare_qreps(self):
        channels = Channel.find(owner_uid=self.user.oid)
        qreps = []
        for c in channels:
            p = self.payload('ClbQRep', str(c.oid))
            qreps.append(QuickReply(c.name, p))
        return qreps

    def on_quick_response(self, action_id, event):
        c = Channel.by_oid(action_id)
        if c:
            return HandlerResult(self.NEXT_CLS_NAME, chid=str(c.oid))

        return self.reinstantiate()

    def on_user_input(self, event):
        if event.is_text_message:
            c = Channel.by_chid_str(event.message_text)
            if c:
                return HandlerResult(self.NEXT_CLS_NAME, chid=str(c.oid))

        return self.reinstantiate()


@step_collection.register
class EditChannelRootChatState(SelectChannelChatState):
    NEXT_CLS_NAME = 'EditChannelTypeChatState'


@step_collection.register
class EditChannelTypeChatState(BasicChatState):
    QREP_CTA = [
        CallToAction('SID_EDIT_CHANNEL_NAME', 'EditChannelNameChatState'),
        CallToAction('SID_EDIT_CHANNEL_DESC', 'EditChannelDescChatState'),
        CallToAction('SID_EDIT_CHANNEL_DELETE', 'DeleteChannelChatState'),
    ]
    MSG_STR_ID = 'SID_SELECT_CHANNEL_EDIT_ACTION'


@step_collection.register
class EditChannelNameChatState(BasicChatState):
    MSG_STR_ID = 'SID_EDIT_CHANNEL_NAME_PROMPT'
    USER_INPUT = True

    def on_user_input(self, event):
        if event.is_text_message:
            c = self._channel
            c.name = event.message_text.strip()
            c.save()
            return self.done('SID_CHANNEL_NAME_CHANGED')

        return self.reinstantiate()


@step_collection.register
class EditChannelDescChatState(BasicChatState):
    MSG_STR_ID = 'SID_EDIT_CHANNEL_DESC_PROMPT'
    USER_INPUT = True

    def on_user_input(self, event):
        if event.is_text_message:
            c = self._channel
            c.desc = event.message_text.strip()
            c.save()
            return self.done('SID_CHANNEL_DESC_CHANGED')

        return self.reinstantiate()


@step_collection.register
class DeleteChannelChatState(BasicChatState):
    MSG_STR_ID = 'SID_DEL_CHANNEL_PROMPT'
    QREP_CTA = [
        CallToAction('SID_YES', 'YesPseudoChatState'),
        CallToAction('SID_NO', 'NoPseudoChatState'),
    ]

    def on_quick_response(self, action_id, event):
        if action_id == 'YesPseudoChatState':
            c = self._channel
            if c:
                c.delete()
                return self.done('SID_CHANNEL_REMOVED')
            else:
                logging.warning("[U#%s] cannot remove nonexistent channel %s",
                                event.sender_id, self.chid)

        if  action_id == 'NoPseudoChatState':
            return self.done('SID_CHANNEL_UNCHANGED')

        return self.reinstantiate()


@step_collection.register
class RootSubscriptionsChatState(BasicChatState):
    QREP_CTA = [
        CallToAction('SID_LIST_SUBSCRIPTIONS', 'SubsListChatState'),
        CallToAction('SID_ADD_SUBSCRIPTION', 'SubAddChatState'),
    ]
    MSG_STR_ID = 'SID_SUBSCRIPTIONS_PROMPT'

    def _prepare_qreps(self):
        qreps = []
        has_subs = True if len(Channel.all_subscribed(self.user.oid)) else False
        for cta in self.QREP_CTA:
            if not has_subs and cta.class_name == 'SubsListChatState':
                continue
            p = self.payload('ClbQRep', cta.action_id)
            qreps.append(QuickReply(cta.title(self.user), p))
        return qreps


@step_collection.register
class SubsListChatState(BasicChatState):
    MSG_STR_ID = 'SID_SELECT_SUB_PROMPT'

    def _prepare_qreps(self):
        qreps = None
        subs = Channel.all_subscribed(self.user.oid)
        if len(subs):
            qreps = []
            for c in subs:
                p = self.payload('ClbQRep', str(c.uchid))
                qreps.append(QuickReply(c.name, p))
        return qreps

    def on_quick_response(self, action_id, event):
        return HandlerResult('SubSelectActionState', chid=action_id)


@step_collection.register
class SubSelectActionState(BasicChatState):
    QREP_CTA = [
        CallToAction('SID_SUB_DELETE', 'SubDelChatState'),
        NoCallToAction('SID_SUB_SHOW_ANNCS'),
    ]
    MSG_STR_ID = 'SID_SELECT_SUB_ACTION_PROMPT'


@step_collection.register
class SubDelChatState(BasicChatState):
    MSG_STR_ID = 'SID_SUB_UNSUBSCRIBE_PROMPT'
    QREP_CTA = [
        CallToAction('SID_YES', 'YesPseudoChatState'),
        CallToAction('SID_NO', 'NoPseudoChatState'),
    ]

    def on_quick_response(self, action_id, event):
        if action_id == 'YesPseudoChatState':
            self._channel.unsubscribe(self.user.oid)
            return self.done('SID_SUB_REMOVED')

        if  action_id == 'NoPseudoChatState':
            return self.done('SID_SUB_UNCHANGED')

        return self.reinstantiate()


@step_collection.register
class SubAddChatState(BasicChatState):
    MSG_STR_ID = 'SID_ENTER_CHANNEL_ID_PROMPT'
    USER_INPUT = True

    def on_user_input(self, event):
        if event.is_text_message:
            c = Channel.by_uchid_str(event.message_text)
            if c:
                self.chid = c.oid
                if self.user.oid in c.subs:
                    return self.done('SID_SUB_EXISTS')
                c.subscribe(self.user.oid)
                if self.user.oid in c.subs:
                    return self.done('SID_SUB_ADDED')
                return self.done('SID_ERROR')

        return self.reinstantiate()


@step_collection.register
class MakeAnncChatState(BasicChatState):
    MSG_STR_ID = 'SID_ANNC_ROOT_PROMPT'
    QREP_CTA = [
        CallToAction('SID_ANNC_NEW_CHANNEL', 'CreateChannelsChatState'),
        CallToAction('SID_ANNC_SELECT_CHANNEL', 'AnncSelectChannelChatState'),
    ]

    def _prepare_qreps(self):
        qreps = []
        for cta in self.QREP_CTA:
            if (not self.has_channels and
                        cta.class_name == 'AnncSelectChannelChatState'):
                continue
            p = self.payload('ClbQRep', cta.action_id)
            qreps.append(QuickReply(cta.title(self.user), p))
        return qreps

    def _get_show_sid(self):
        if self.has_channels:
            return 'SID_ANNC_ROOT_PROMPT'
        return 'SID_ANNC_CREATE_CHANNEL_PROMPT'

    def show(self):
        self.has_channels = (len(Channel.find(owner_uid=self.user.oid)) != 0)
        super().show()


@step_collection.register
class AnncSelectChannelChatState(SelectChannelChatState):
    NEXT_CLS_NAME = 'AnncGetTitleChatState'


@step_collection.register
class AnncGetTitleChatState(BasicChatState):
    MSG_STR_ID = 'SID_ANNC_GET_TITLE_PROMPT'
    USER_INPUT = True

    def create_annc(self, title):
        a = Annc(title=title, chid=self.chid, owner_uid=self.user.oid)
        a.save()
        return a

    def on_user_input(self, event):
        if event.is_text_message:
            logging.debug("[U#%s] Desired annc title is: %s",
                          event.sender_id, event.message_text)
            a = self.create_annc(event.message_text)
            return HandlerResult('AnncGetTextChatState', aid=str(a.oid))

        return self.reinstantiate()


@step_collection.register
class AnncGetTextChatState(BasicChatState):
    MSG_STR_ID = 'SID_ANNC_GET_TEXT_PROMPT'
    USER_INPUT = True

    def on_user_input(self, event):
        if event.is_text_message:
            a = self._announcement
            a.text = event.message_text.strip()
            a.save()
            Horn(self.page).notify(a)
            return self.done('SID_ANNC_DONE')

        return self.reinstantiate()


class BotRef(object):
    PARAMS_DELIMITER = ';'
    KEYVAL_DELIMITER = ':'

    @classmethod
    def get_ref(cls, **kwargs):
        ref = ''
        for k in kwargs:
            if ref != '':
                ref += cls.PARAMS_DELIMITER
            ref += k + cls.KEYVAL_DELIMITER + kwargs[k]
        return ref

    @classmethod
    def get_params(cls, ref):
        d = {}
        params = ref.split(cls.PARAMS_DELIMITER)
        for p in params:
            v = p.split(cls.KEYVAL_DELIMITER)
            if v and len(v) == 2:
                d[v[0]] = v[1]
        return d

    def __init__(self, ref=None, **kwargs):
        self.params = self.get_params(ref) if ref else {}
        if kwargs:
            self.add_params(**kwargs)

    def add_params(self, **kwargs):
        self.params.update(**kwargs)

    @property
    def ref(self):
        return self.get_ref(**self.params)

    def __str__(self):
        return self.ref


class BotChat(object):
    MENU_CTA = [
        CallToAction('SID_MENU_ANNOUNCEMENTS', 'MakeAnncChatState'),
        CallToAction('SID_MENU_CHANNELS', 'RootChannelsChatState'),
        CallToAction('SID_MENU_SUBSCRIPTIONS', 'RootSubscriptionsChatState'),
        CallToAction('SID_MENU_HELP', 'RootHelpChatState'),
    ]
    REF_SUBSCRIBE_ACTION = 'sub'

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
                                                              p.param,
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
        if event.is_postback_referral:
            logging.debug("[U#%s] postback ref: %s, %s", event.sender_id,
                          event.postback_referral,
                          event.postback_referral_ref)
            self.on_ref(event.postback_referral_ref)
        self.state.show()

    def on_referral(self, event):
        logging.debug("[U#%s] ref: %s, %s", event.sender_id,
                          event.referral,
                          event.referral_ref)
        self.on_ref(event.referral_ref)

    def on_action(self, type, action_id, param, event):
        logging.debug("%s: on_action(%s): %s arrived",
                      self.class_name(), type, action_id)
        if type == 'ClbMenu':
            result = self._on_menu(action_id, event)
        else:
            result = self.state.on_action(type, action_id, param, event)
        if result:
            self.instantiate_state(result)
            self.state.show()

    def on_ref(self, ref):
        r = BotRef(ref=ref)
        if self.REF_SUBSCRIBE_ACTION in r.params:
            c = Channel.find_unique(uchid=r.params[self.REF_SUBSCRIBE_ACTION])
            if c:
                if self.user.oid in c.subs:
                    sid = 'SID_SUB_EXISTS'
                else:
                    c.subscribe(self.user.oid)
                    sid = 'SID_SUB_ADDED' if self.user.oid in c.subs else 'SID_ERROR'
                msg = str(BotString(sid, user=self.user, channel=c))
                self.page.send(self.user.fbid, msg)
        else:
            logging.warning("[U#%s] unsupported ref: %s", self.user.oid, ref)


def chat_clb_handler(user, page, payload, event):
    logging.debug("[U#%s] Clb Handler: %s", event.sender_id, payload)
    BotChat.clb_by_payload(user, page, payload, event)


def chat_menu_handler(user, page, payload, event):
    logging.debug("[U#%s] Menu Handler: %s", event.sender_id, payload)
    BotChat.clb_by_payload(user, page, payload, event)


def chat_msg_handler(user, page, payload, event):
    logging.debug("[U#%s] Msg Handler: %s", event.sender_id, payload)
    BotChat.clb_by_payload(user, page, payload, event)
