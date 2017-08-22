import logging
from collections import namedtuple
from fbmq import QuickReply, Template, Attachment
from bot.translations import BotString
from db import Channel, Annc, UpdateOps, m_link
from bot.horn import Horn


BotChatClbTypes = dict(
    ClbQRep="CHAT_CLB_QREP",
    ClbMenu="CHAT_CLB_MENU",
    ClbMsg="CHAT_CLB_MSG"
)


HOW_TO_ACTION_ID='HowToAction'


class Payload(object):
    DELIMITER='/'
    SUB_DELIMITER = ':'

    @classmethod
    def from_string(cls, payload):
        params = payload.split(cls.DELIMITER)

        for k, v in BotChatClbTypes.items():
            if params[0] == v and 3 <= len(params) <= 4:
                channel = None
                annc = None
                if len(params) == 4:
                    p = params[3].split(cls.SUB_DELIMITER)
                    if p[0] == 'ch':
                        channel = Channel.by_oid(p[1])
                    elif p[0] == 'an':
                        annc = Annc.by_oid(p[1])
                        channel = Channel.by_oid(annc.chid)
                return cls(k, params[1], params[2], channel=channel, annc=annc)

        return None

    def __init__(self, type, state, action_id, channel=None, annc=None):
        if not type or not action_id or not state:
            raise ValueError(
                "{}: all fields are mandatory".format(self.__name__))
        self.type = type
        self.state = state
        self.action_id = action_id
        self.channel = channel
        self.annc = annc

    def __str__(self):
        s = BotChatClbTypes[self.type] + self.DELIMITER + \
            self.state + self.DELIMITER + self.action_id
        if self.annc:
            s = s + self.DELIMITER +\
                'an' + self.SUB_DELIMITER + str(self.annc.oid)
        elif self.channel:
            s = s + self.DELIMITER +\
                'ch' + self.SUB_DELIMITER + str(self.channel.oid)
        return s


CTA = namedtuple('CTA', ['sid', 'action_id'])


class CTAList(object):
    def __init__(self, sm, c=None):
        self.ctas = []
        self.sm = sm
        if c:
            self.add(c)

    def add(self, c):
        assert c
        if isinstance(c, CTA):
            self.ctas.append(c)
        elif isinstance(c, list):
            self.ctas.extend(c)
        else:
            raise TypeError("Incorrect type: {}".format(type(c)))

    @property
    def quick_replies(self):
        qreps = []
        for cta in self.ctas:
            p = Payload(type='ClbQRep',
                        state=self.sm.state,
                        action_id=cta.action_id,
                        channel=self.sm.channel,
                        annc = self.sm.annc)
            if cta.sid.startswith('SID_'):
               title = str(BotString(cta.sid,
                                     user=self.sm.user,
                                     channel=self.sm.channel,
                                     annc=self.sm.annc))
            else:
                title = cta.sid
            qreps.append(QuickReply(title, str(p)))
        return qreps if qreps else None

    @property
    def buttons(self):
        buttons = []
        for cta in self.ctas:
            p = Payload(type='ClbQRep',
                        state=self.sm.state,
                        action_id=cta.action_id,
                        channel=self.sm.channel,
                        annc = self.sm.annc)
            if cta.sid.startswith('SID_'):
               title = str(BotString(cta.sid,
                                     user=self.sm.user,
                                     channel=self.sm.channel,
                                     annc=self.sm.annc))
            else:
                title = cta.sid
            buttons.append(Template.ButtonPostBack(title, str(p)))
        return buttons if buttons else None

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


class BaseStateMachine(object):
    HANDLERS = dict()
    INITIATORS = dict()
    HELPERS = dict()

    @classmethod
    def state_initiator(cls, state):
        def actual_decorator(func):
            assert state not in cls.INITIATORS
            cls.INITIATORS[state] = func
        return actual_decorator

    @classmethod
    def state_handler(cls, state):
        def actual_decorator(func):
            assert state not in cls.HANDLERS
            cls.HANDLERS[state] = func
        return actual_decorator

    @classmethod
    def state_helper(cls, state):
        def actual_decorator(func):
            assert state not in cls.HELPERS
            cls.HELPERS[state] = func
        return actual_decorator

    def __init__(self, user=None, channel=None, annc=None, state=None):
        self._state = None
        self.user = user
        self.channel = channel
        self.annc = annc
        if state:
            self.set_state(state=state)

    def call_initiator(self, **kwargs):
        if self._state not in self.INITIATORS:
            raise ValueError(
                "State with no initiator: {}".format(self._state))
        self.INITIATORS[self._state](self)

    def call_handler(self, event):
        if self._state not in self.HANDLERS:
            raise ValueError(
                "State with no handler: {}".format(self._state))
        self.HANDLERS[self._state](self, event=event)

    def call_helper(self, event):
        if self._state not in self.HELPERS:
            logging.warning("State with no helper: %s", self._state)
        else:
            self.HELPERS[self._state](self, event=event)

    def set_state(self, state):
        if state not in self.INITIATORS and state not in self.HANDLERS:
            raise ValueError(
                "Unknown State: {}".format(state))
        self._state = state

    @property
    def state(self):
        return self._state


class BotChat(BaseStateMachine):
    REF_SUBSCRIBE_ACTION = 'sub'
    FB_MAX_GENERIC_TEMPLATE_ELEMENTS = 10 # elements is limited to 10

    @classmethod
    def class_name(cls):
        return cls.__name__

    @property
    def howto_qreps(self):
        return CTAList(self,[CTA(sid='SID_HOW_TO',
                                 action_id=HOW_TO_ACTION_ID)]).quick_replies

    def set_state(self, state):
        if state != self.state:
            super().set_state(state=state)

    def call_initiator(self, **kwargs):
        super().call_initiator(**kwargs)
        p = Payload(type='ClbMsg', state=self.state, action_id='UsrInput',
                    channel=self.channel, annc=self.annc)
        self.user.update(UpdateOps.Supported.SET, state_payload=str(p))

    def send_simple(self, msg_sid, ctas = None, howto=True):
        qreps = None
        if howto:
            qreps = self.howto_qreps
        msg = str(BotString(msg_sid, user=self.user, channel=self.channel))
        if ctas:
            self.page.send(self.user.fbid,
                           Template.Buttons(msg, CTAList(self, ctas).buttons),
                           quick_replies=qreps)
        else:
            self.page.send(self.user.fbid, msg, quick_replies=qreps)

    def _state_init_select_channel(self, channels, ctas):
        ccnt = len(channels)
        skip = 0
        while skip < ccnt:
            last = min(skip + self.FB_MAX_GENERIC_TEMPLATE_ELEMENTS, ccnt)
            elements = []
            for c in channels[skip:last]:
                buttons = []
                for cta in ctas:
                    pstr = str(Payload(type='ClbQRep',
                                       state=self.state,
                                       action_id=cta.action_id,
                                       channel=c))
                    title = str(BotString(cta.sid, channel=c))
                    buttons.append(Template.ButtonPostBack(title, pstr))
                t = Template.GenericElement(c.name,
                                            subtitle=c.desc + '\n' + c.str_uchid,
                                            image_url=c.cover_pic,
                                            buttons=buttons)
                elements.append(t)
            skip = last
            self.page.send(self.user.fbid, Template.Generic(elements),
                           quick_replies=self.howto_qreps)

    def _state_handle_select_channel(self, event):
        if event.is_postback:
            p = Payload.from_string(event.postback_payload)
            self.channel = p.channel
            return p.action_id
        return None

    def _state_handler_edit_channel_field(self, fname, event):
        if not event.is_text_message:
            return False
        val = event.message_text.strip()
        self.channel.update(op=UpdateOps.Supported.SET,**{fname: val})
        return True

    def _state_handler_default(self, event):
        if event.is_quick_reply:
            p = Payload.from_string(event.quick_reply_payload)
            assert p.action_id == HOW_TO_ACTION_ID
            self.call_helper(event)
        elif event.is_postback:
            p = Payload.from_string(event.postback_payload)
            self.set_state(p.action_id)
        elif event.is_text_message:
            pass
        else:
            pass

    @BaseStateMachine.state_initiator('Acquaintance')
    def state_init_acquaintance(self):
        ctas = [
            CTA(sid='SID_MY_CHANNELS', action_id='MyChannels'),
            CTA(sid='SID_MY_SUBSCRIPTIONS', action_id='MySubscriptions'),
            CTA(sid='SID_HOW_TO', action_id=HOW_TO_ACTION_ID)
        ]
        self.send_simple('SID_ACQUAINTANCE_PROMPT', ctas=ctas, howto=False)

    @BaseStateMachine.state_handler('Acquaintance')
    def state_handler_acquaintance(self, event):
        if event.is_postback:
            p = Payload.from_string(event.postback_payload)
            if p.action_id == HOW_TO_ACTION_ID:
                self.call_helper(event)
                return
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('Root')
    def state_init_root(self):
        ctas = [
            CTA(sid='SID_MY_SUBSCRIPTIONS', action_id='MySubscriptions'),
            CTA(sid='SID_MAKE_ANNOUNCEMENT', action_id='MakeAnnouncement'),
            CTA(sid='SID_MY_CHANNELS', action_id='MyChannels'),
        ]
        self.send_simple('SID_ROOT_PROMPT', ctas=ctas)

    @BaseStateMachine.state_handler('Root')
    def state_handler_root(self, event):
        self._state_handler_default(event=event)


    @BaseStateMachine.state_initiator('NotImplemented')
    def state_init_not_implemented(self):
        ctas = [
            CTA(sid='SID_MY_SUBSCRIPTIONS', action_id='MySubscriptions'),
            CTA(sid='SID_MAKE_ANNOUNCEMENT', action_id='MakeAnnouncement'),
            CTA(sid='SID_MY_CHANNELS', action_id='MyChannels'),
        ]
        self.send_simple('SID_DBG_NO_ACTION', ctas=ctas)

    @BaseStateMachine.state_handler('NotImplemented')
    def state_handler_not_implemented(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('MyChannels')
    def state_init_my_channels(self):
        channels = Channel.find(owner_uid=self.user.oid)
        ctas = [CTA(sid='SID_CREATE_CHANNEL', action_id='CreateChannel')]
        if len(channels):
            ctas.append(CTA(sid='SID_BROWSE_CHANNELS',
                            action_id='BrowseChannels'))
        self.send_simple('SID_MY_CHANNELS_PROMPT', ctas=ctas)

    @BaseStateMachine.state_handler('MyChannels')
    def state_handle_my_channels(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('MySubscriptions')
    def state_init_my_subscriptions(self):
        subs = Channel.all_subscribed(self.user.oid)
        ctas = [CTA(sid='SID_ADD_SUBSCRIPTION', action_id='AddSub')]
        if len(subs):
            ctas.append(CTA(sid='SID_LIST_SUBSCRIPTIONS',
                            action_id='ListSubs'))
        self.send_simple('SID_SUBSCRIPTIONS_PROMPT', ctas=ctas)

    @BaseStateMachine.state_handler('MySubscriptions')
    def state_handler_my_subscriptions(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('MakeAnnouncement')
    def state_init_make_annc(self):
        channels = Channel.find(owner_uid=self.user.oid)
        ctas = [CTA(sid='SID_ANNC_NEW_CHANNEL', action_id='CreateChannel')]
        if len(channels):
            ctas.append(CTA(sid='SID_ANNC_SELECT_CHANNEL',
                            action_id='AnncSelectChannel'))
            msg_sid = 'SID_ANNC_ROOT_PROMPT'
        else:
            msg_sid = 'SID_ANNC_CREATE_CHANNEL_PROMPT'
        self.send_simple(msg_sid=msg_sid, ctas=ctas)

    @BaseStateMachine.state_handler('MakeAnnouncement')
    def state_handler_make_annc(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('CreateChannel')
    def state_init_create_channel(self):
        self.send_simple('SID_GET_CHANNEL_NAME')

    @BaseStateMachine.state_handler('CreateChannel')
    def state_handler_create_channel(self, event):
        if event.is_text_message:
            logging.debug("[U#%s] Desired channel name is: %s",
                          event.sender_id, event.message_text)
            c = Channel.create(name=event.message_text,
                               owner_uid=self.user.oid)
            r = BotRef(sub=c.uchid)
            mc = self.page.get_messenger_code(ref=r.ref)
            c.set_code(ref=r.ref, messenger_code_url=mc)
            self.channel = c
            self.set_state('SetChannelDesc')
        else:
            self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('SetChannelDesc')
    def state_init_set_channel_desc(self):
        self.send_simple('SID_GET_CHANNEL_DESC')

    @BaseStateMachine.state_handler('SetChannelDesc')
    def state_handler_set_channel_desc(self, event):
        assert self.channel
        if self._state_handler_edit_channel_field(fname='desc', event=event):
            logging.debug("[U#%s] Desired %s channel desc is: %s",
                          event.sender_id, self.channel.oid, self.channel.desc)
            self.set_state('SetChannelPic')
        else:
            self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('SetChannelPic')
    def state_init_set_channel_pic(self):
        ctas = [CTA(sid='SID_DONE', action_id='Root')]
        self.send_simple('SID_GET_CHANNEL_PIC', ctas=ctas)

    @BaseStateMachine.state_handler('SetChannelPic')
    def state_handler_set_channel_pic(self, event):
        assert self.channel
        if event.is_attachment_message:
            for a in event.message_attachments:
                if a['type'] == 'image':
                    self.channel.set_cover_pic(a['payload']['url'])
                    break
            self.send_simple('SID_CHANNEL_CREATED')
            self.set_state('Root')
        elif event.is_postback:
            p = Payload.from_string(event.postback_payload)
            assert p.action_id == 'Root'
            self.send_simple('SID_CHANNEL_CREATED')
            self.set_state(p.action_id)
        else:
            self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('BrowseChannels')
    def state_init_browse_channels(self):
        channels = Channel.find(owner_uid=self.user.oid)
        ctas = [
            CTA(sid='SID_VIEW_CHANNEL_BTN', action_id='NotImplemented'),
            CTA(sid='SID_EDIT_CHANNEL_BTN', action_id='SelectEditChannelType'),
            CTA(sid='SID_SHARE_CHANNEL_BTN', action_id='SelectShareChannelType'),
        ]
        self._state_init_select_channel(channels=channels, ctas=ctas)

    @BaseStateMachine.state_handler('BrowseChannels')
    def state_handler_browse_channels(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('SelectEditChannelType')
    def state_init_select_edit_channel_type(self):
        ctas = [
            CTA(sid='SID_EDIT_CHANNEL_NAME', action_id='EditChannelName'),
            CTA(sid='SID_EDIT_CHANNEL_DESC', action_id='EditChannelDesc'),
            CTA(sid='SID_EDIT_CHANNEL_DELETE', action_id='DeleteChannel')
        ]
        self.send_simple('SID_SELECT_CHANNEL_EDIT_ACTION', ctas=ctas)

    @BaseStateMachine.state_handler('SelectEditChannelType')
    def state_handler_select_edit_channel_type(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('SelectShareChannelType')
    def state_init_select_edit_channel_type(self):
        title = str(BotString('SID_SELECT_CHANNEL_SHARE_ACTION',
                              user=self.user, channel=self.channel))
        buttons = [
            Template.ButtonShare(),
            Template.ButtonWeb(
                str(BotString('SID_SHARE_CHANNEL_BY_LINK',
                              user=self.user,
                              channel=self.channel)),
                m_link(BotRef(sub=self.channel.uchid).ref)),
            Template.ButtonPostBack(
                str(BotString('SID_MORE',
                              user=self.user,
                              channel=self.channel)),
                str(Payload(type='ClbQRep',
                            state=self.state,
                            action_id='SelectShareChannelTypeEx',
                            channel=self.channel)))
        ]
        e = Template.GenericElement(title,
                                    image_url=self.channel.cover_pic,
                                    buttons=buttons)
        self.page.send(self.user.fbid, Template.Generic([ e ]))

    @BaseStateMachine.state_handler('SelectShareChannelType')
    def state_handler_select_edit_channel_type(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('SelectShareChannelTypeEx')
    def state_init_select_edit_channel_type_ex(self):
        title = str(BotString('SID_SELECT_CHANNEL_SHARE_ACTION',
                              user=self.user, channel=self.channel))
        buttons = [
            Template.ButtonPostBack(
                str(BotString('SID_SHARE_CHANNEL_BY_MSG_CODE',
                              user=self.user,
                              channel=self.channel)),
                str(Payload(type='ClbQRep',
                            state=self.state,
                            action_id='ByMsgCode',
                            channel=self.channel))),
            Template.ButtonPostBack(
                str(BotString('SID_SHARE_CHANNEL_BY_QR_CODE',
                              user=self.user,
                              channel=self.channel)),
                str(Payload(type='ClbQRep',
                            state=self.state,
                            action_id='ByQRCode',
                            channel=self.channel))),
            Template.ButtonPostBack(
                str(BotString('SID_SHARE_CHANNEL_BY_UCHID',
                              user=self.user,
                              channel=self.channel)),
                str(Payload(type='ClbQRep',
                            state=self.state,
                            action_id='ByUChID',
                            channel=self.channel)))
        ]
        e = Template.GenericElement(title,
                                    image_url=self.channel.cover_pic,
                                    buttons=buttons)
        self.page.send(self.user.fbid, Template.Generic([ e ]))

    @BaseStateMachine.state_handler('SelectShareChannelTypeEx')
    def state_handler_select_edit_channel_type_ex(self, event):
        if event.is_postback:
            p = Payload.from_string(event.postback_payload)
            if p.action_id == 'ByMsgCode':
                self.page.send(self.user.fbid,
                               Attachment.Image(self.channel.messenger_code))
            elif p.action_id == 'ByQRCode':
                self.page.send(self.user.fbid,
                               Attachment.Image(self.channel.qr_code))
            elif p.action_id == 'ByUChID':
                self.page.send(self.user.fbid,
                               str(BotString('SID_SHARE_BY_UCHID_TEXT',
                                             user=self.user,
                                             channel=self.channel)))
            self.set_state('Root')
        else:
            self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('EditChannelName')
    def state_init_edit_channel_name(self):
        self.send_simple('SID_EDIT_CHANNEL_NAME_PROMPT')

    @BaseStateMachine.state_handler('EditChannelName')
    def state_handler_edit_channel_name(self, event):
        if self._state_handler_edit_channel_field(fname='name', event=event):
            self.send_simple('SID_CHANNEL_NAME_CHANGED')
            self.set_state('Root')
        else:
            self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('EditChannelDesc')
    def state_init_edit_channel_name(self):
        self.send_simple('SID_EDIT_CHANNEL_DESC_PROMPT')

    @BaseStateMachine.state_handler('EditChannelDesc')
    def state_handler_edit_channel_name(self, event):
        if self._state_handler_edit_channel_field(fname='desc', event=event):
            self.send_simple('SID_CHANNEL_DESC_CHANGED')
            self.set_state('Root')
        else:
            self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('DeleteChannel')
    def state_init_delete_channel(self):
        ctas = [
            CTA(sid='SID_YES', action_id='YesPseudoChatState'),
            CTA(sid='SID_NO', action_id='NoPseudoChatState')
        ]
        self.send_simple('SID_DEL_CHANNEL_PROMPT', ctas=ctas)

    @BaseStateMachine.state_handler('DeleteChannel')
    def state_handler_delete_channel(self, event):
        if event.is_quick_reply:
            p = Payload.from_string(event.quick_reply_payload)
            if p.action_id == 'YesPseudoChatState':
                self.channel.delete()
                self.channel = None
                self.send_simple('SID_CHANNEL_REMOVED')
            else:
                self.send_simple('SID_CHANNEL_UNCHANGED')
            self.set_state('Root')
        else:
             self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('ListSubs')
    def state_init_list_subs(self):
        channels = Channel.all_subscribed(uid=self.user.oid)
        ctas = [
            CTA(sid='SID_VIEW_SUB_BTN', action_id='NotImplemented'),
            CTA(sid='SID_DEL_SUB_BTN', action_id='DelSub'),
            CTA(sid='SID_SHARE_SUB_BTN', action_id='NotImplemented'),
        ]
        self._state_init_select_channel(channels=channels, ctas=ctas)

    @BaseStateMachine.state_handler('ListSubs')
    def state_handler_list_subs(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('AddSub')
    def state_init_add_sub(self):
        self.send_simple('SID_ENTER_CHANNEL_ID_PROMPT')

    @BaseStateMachine.state_handler('AddSub')
    def state_handler_add_sub(self, event):
        if event.is_text_message:
            logging.debug("[U#%s] Desired uchid is: %s",
                          event.sender_id, event.message_text)
            self.channel = Channel.by_uchid_str(event.message_text)
            if self.channel:
                if self.user.oid in self.channel.subs:
                    self.send_simple('SID_SUB_EXISTS')
                else:
                    self.channel.subscribe(self.user.oid)
                    if self.user.oid in self.channel.subs:
                        self.send_simple('SID_SUB_ADDED')
                        self.set_state('Root')
                    else:
                        self.send_simple('SID_ERROR')

    @BaseStateMachine.state_initiator('DelSub')
    def state_init_del_sub(self):
        ctas = [
            CTA(sid='SID_YES', action_id='YesPseudoChatState'),
            CTA(sid='SID_NO', action_id='NoPseudoChatState')
        ]
        self.send_simple('SID_SUB_UNSUBSCRIBE_PROMPT', ctas)

    @BaseStateMachine.state_handler('DelSub')
    def state_handler_del_sub(self, event):
        if event.is_quick_reply:
            p = Payload.from_string(event.quick_reply_payload)
            if p.action_id == 'YesPseudoChatState':
                self.channel.unsubscribe(self.user.oid)
                self.channel = None
                self.send_simple('SID_SUB_REMOVED')
            else:
                self.send_simple('SID_SUB_UNCHANGED')
            self.set_state('Root')
        else:
             self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('AnncSelectChannel')
    def state_init_annc_select_channel(self):
        channels = Channel.find(owner_uid=self.user.oid)
        ctas = [
            CTA(sid='SID_SELECT_THIS', action_id='MakeAnnc'),
        ]
        self._state_init_select_channel(channels=channels, ctas=ctas)

    @BaseStateMachine.state_handler('AnncSelectChannel')
    def state_handler_annc_select_channel(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('MakeAnnc')
    def state_init_make_annc(self):
        self.send_simple('SID_ANNC_GET_TITLE_PROMPT')

    @BaseStateMachine.state_handler('MakeAnnc')
    def state_handler_make_annc(self, event):
        if event.is_text_message:
            logging.debug("[U#%s] Desired annc title is: %s",
                          event.sender_id, event.message_text)
            self.annc = Annc(title=event.message_text,
                             chid=self.channel.oid,
                             owner_uid=self.user.oid)
            self.annc.save()
            self.set_state('SetAnncText')
        else:
            self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('SetAnncText')
    def state_init_set_annc_text(self):
        self.send_simple('SID_ANNC_GET_TEXT_PROMPT')

    @BaseStateMachine.state_handler('SetAnncText')
    def state_handler_set_annc_text(self, event):
        if event.is_text_message:
            self.annc.update(op=UpdateOps.Supported.SET,
                             text=event.message_text.strip())
            self.send_simple('SID_ANNC_DONE')
            Horn(self.page).notify(self.annc)
            self.annc = None
            self.set_state('Root')
        else:
            self._state_handler_default(event=event)

    @classmethod
    def clb_by_payload(cls, user, page, payload, event):
        p = Payload.from_string(payload)
        if p:
            logging.debug("[U#%s] clb arrived: %s (type=%s)",
                          event.sender_id, payload, p.type)
            sm = cls(page=page, user=user, state= p.state,
                     channel=p.channel, annc=p.annc)
            sm.on_action(event)
        else:
            logging.warning("[U#%s] clb: bad payload: %s",
                            event.sender_id, payload)

    @classmethod
    def get_menu_buttons(cls):
        menu_items = [
            CTA(sid='SID_MENU_SUBSCRIPTIONS', action_id='MySubscriptions'),
            CTA(sid='SID_MENU_ANNOUNCEMENTS', action_id= 'MakeAnnouncement'),
            CTA(sid='SID_MENU_CHANNELS', action_id='MyChannels'),
        ]
        buttons = []
        for cta in menu_items:
            p = Payload(type='ClbMenu', state='Root', action_id=cta.action_id)
            btn = Template.ButtonPostBack(str(BotString(cta.sid)), str(p))
            buttons.append(btn)
        return buttons

    def _on_menu(self, event):
        self._state_handler_default(event=event)

    def __init__(self, page, user, state='Acquaintance',
                 channel=None, annc=None):
        self.page = page
        super().__init__(user=user, state=state, channel=channel, annc=annc)

    def start(self, event):
        if event.is_postback_referral:
            logging.debug("[U#%s] postback ref: %s, %s", event.sender_id,
                          event.postback_referral,
                          event.postback_referral_ref)
            self.on_ref(event.postback_referral_ref)
        self.call_initiator()

    def on_referral(self, event):
        logging.debug("[U#%s] ref: %s, %s", event.sender_id,
                          event.referral,
                          event.referral_ref)
        self.on_ref(event.referral_ref)

    def on_action(self, event):
        self.call_handler(event)
        self.call_initiator()

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


def chat_msg_handler(user, page, event):
    logging.debug("[U#%s] Msg Handler: %s", event.sender_id,
                  user.state_payload)
    BotChat.clb_by_payload(user, page, user.state_payload, event)
