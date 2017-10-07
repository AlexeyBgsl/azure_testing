import logging
from fbmq import QuickReply, Template, Attachment
from bot.translations import BotString
from db import Channel, Annc, DCRS, UpdateOps, m_link
from bot.horn import Horn
from bot.config import CONFIG
from bot.mail import GMailer


BotChatClbTypes = dict(
    ClbQRep="CHAT_CLB_QREP",
    ClbMenu="CHAT_CLB_MENU",
    ClbMsg="CHAT_CLB_MSG"
)


FEEDBACK_ACTION_ID='FeedbackAction'


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
                        channel = DCRS.Channels.by_oid(p[1])
                    elif p[0] == 'an':
                        annc = DCRS.Anncs.by_oid(p[1])
                        channel = DCRS.Channels.by_oid(annc.chid)
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


class CTA(object):
    ACTION_TYPE_POSTBACK = 0
    ACTION_TYPE_WEB = 1
    ACTION_TYPE_SHARE = 2

    def __init__(self, sid=None, action_id=None,
                 action_type=ACTION_TYPE_POSTBACK):
        self.sid = sid
        self.action_id = action_id
        self.action_type = action_type


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
            assert cta.action_type == CTA.ACTION_TYPE_POSTBACK
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

    def get_buttons(self, channel=None, annc=None):
        buttons = []
        c = channel if channel else self.sm.channel
        a = annc if annc else self.sm.annc
        for cta in self.ctas:
            if not cta.sid:
                title = None
            elif cta.sid.startswith('SID_'):
                title = str(BotString(cta.sid,
                                      user=self.sm.user,
                                      channel=c,
                                      annc=a))
            else:
                title = cta.sid

            if cta.action_type == CTA.ACTION_TYPE_POSTBACK:
                p = Payload(type='ClbQRep',
                            state=self.sm.state,
                            action_id=cta.action_id,
                            channel=c,
                            annc = a)
                buttons.append(Template.ButtonPostBack(title, str(p)))
            elif cta.action_type == CTA.ACTION_TYPE_SHARE:
                buttons.append(Template.ButtonShare())
            elif cta.action_type == CTA.ACTION_TYPE_WEB:
                buttons.append(Template.ButtonWeb(title, cta.action_id))
            else:
                raise ValueError("Unsupported action type: {}".format(
                    cta.action_type))

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
    def std_qreps(self):
        return CTAList(self,[CTA(sid='SID_FEEDBACK',
                                 action_id=FEEDBACK_ACTION_ID)
                             ]).quick_replies

    def set_state(self, state):
        if state != self.state:
            super().set_state(state=state)

    def call_initiator(self, **kwargs):
        super().call_initiator(**kwargs)
        p = Payload(type='ClbMsg', state=self.state, action_id='UsrInput',
                    channel=self.channel, annc=self.annc)
        self.user.update(UpdateOps.Supported.SET, state_payload=str(p))

    def send_simple(self, msg_sid, ctas = None, std_quick_replies=True,
                    channel=None):
        qreps = None
        if std_quick_replies:
            qreps = self.std_qreps
        msg = str(BotString(msg_sid,
                            user=self.user,
                            channel=channel if channel else self.channel))
        if ctas:
            self.page.send(self.user.fbid,
                           Template.Buttons(msg,
                                            CTAList(self, ctas).get_buttons()),
                           quick_replies=qreps)
        else:
            self.page.send(self.user.fbid, msg, quick_replies=qreps)

    def _state_init_show_anncs(self):
        assert self.channel
        anncs = DCRS.Anncs.find(chid=self.channel.oid)
        acnt = len(anncs)
        skip = 0
        if hasattr(self, 'anncs_to_skip'):
            skip = getattr(self, 'anncs_to_skip')
            delattr(self, 'anncs_to_skip')
        last = min(skip + 5, acnt)
        if acnt > skip:
            for a in anncs[skip:last]:
                Horn(self.page).notify_one(user=self.user,
                                           annc=a,
                                           channel=self.channel)
        if acnt <= skip or last == acnt:
            self.send_simple('SID_NO_MORE_ANNCS')
            self.set_state('Root')
        else:
            ctas = [
                CTA(sid='SID_YES', action_id=str(last)),
                CTA(sid='SID_NO', action_id='-1')
            ]
            self.send_simple('SID_SHOW_EARIER_ANNCS_PROMPT', ctas=ctas)

    def _state_handle_show_anncs(self, event):
        if event.is_postback:
            p = Payload.from_string(event.postback_payload)
            if p.action_id == '-1':
                self.set_state('Root')
            else:
                setattr(self, 'anncs_to_skip', int(p.action_id))
        else:
            self._state_handler_default(event=event)

    def _state_init_select_channel(self, channels, ctas):
        ccnt = len(channels)
        skip = 0
        while skip < ccnt:
            last = min(skip + self.FB_MAX_GENERIC_TEMPLATE_ELEMENTS, ccnt)
            elements = []
            for c in channels[skip:last]:
                buttons = CTAList(self, ctas).get_buttons(channel=c)
                subtitle = c.desc + '\n' + c.str_uchid
                t = Template.GenericElement(c.name,
                                            subtitle=subtitle,
                                            image_url=c.cover_pic,
                                            buttons=buttons)
                elements.append(t)
            skip = last
            self.page.send(self.user.fbid, Template.Generic(elements,
                                                            square_image=True),
                           quick_replies=self.std_qreps)

    def _state_handle_select_channel(self, event):
        if event.is_postback:
            p = Payload.from_string(event.postback_payload)
            self.channel = p.channel
            return p.action_id
        return None

    def _state_handler_edit_channel_field(self, fname, event, skip_val=None):
        if not event.is_text_message:
            return False
        val = event.message_text.strip()
        if not val:
            return False
        if skip_val and skip_val.lower() == val.lower():
            return True
        self.channel.update(op=UpdateOps.Supported.SET,**{fname: val})
        return True

    def _state_handler_add_sub(self, event):
        if event.is_text_message:
            logging.debug("[U#%s] Desired uchid is: %s",
                          event.sender_id, event.message_text)
            channel = DCRS.Channels.by_uchid_str(event.message_text)
            if channel:
                if self.user.oid in channel.subs:
                    self.send_simple('SID_SUB_EXISTS', channel=channel)
                else:
                    channel.subscribe(self.user.oid)
                    if self.user.oid in channel.subs:
                        self.channel = channel
                        self.send_simple('SID_SUB_ADDED')
                        return True
                    else:
                        self.send_simple('SID_ERROR', channel=channel)
        return False

    def _state_handler_default(self, event):
        if event.is_quick_reply:
            p = Payload.from_string(event.quick_reply_payload)
            if p.action_id == FEEDBACK_ACTION_ID:
                self.set_state('Feedback')
            else:
                raise TypeError(
                    "Incorrect Quick Reply: {}".format(p.action_id))
        elif event.is_postback:
            p = Payload.from_string(event.postback_payload)
            self.set_state(p.action_id)
        elif event.is_text_message:
            pass
        else:
            pass

    def _state_init_select_share_channel_type(self):
        ctas = [
            CTA(action_type=CTA.ACTION_TYPE_SHARE),
            CTA(sid='SID_CHANNEL_INFO',
                action_id=CONFIG['CHANNELS_INFO_URI'] + self.channel.uchid,
                action_type=CTA.ACTION_TYPE_WEB),
            CTA(sid='SID_ADD_SUBSCRIPTION',
                action_id=m_link(BotRef(sub=self.channel.uchid).ref),
                action_type=CTA.ACTION_TYPE_WEB),
        ]
        self._state_init_select_channel(channels=[self.channel, ],
                                        ctas=ctas)

    def _state_handler_select_share_channel_type(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('Acquaintance')
    def state_init_acquaintance(self):
        ctas = [
            CTA(sid='SID_MY_CHANNELS', action_id='MyChannels'),
            CTA(sid='SID_MY_SUBSCRIPTIONS', action_id='MySubscriptions'),
        ]
        self.send_simple('SID_ACQUAINTANCE_PROMPT', ctas=ctas,
                         std_quick_replies=False)

    @BaseStateMachine.state_handler('Acquaintance')
    def state_handler_acquaintance(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('Feedback')
    def state_init_feedback(self):
        self.send_simple('SID_FEEDBACK_PROMPT', std_quick_replies=False)

    @BaseStateMachine.state_handler('Feedback')
    def state_handler_feedback(self, event):
        if event.is_text_message:
            g = GMailer(sender_gmail=CONFIG['FEEDBACK_SENDER_GMAIL'],
                        pwd=CONFIG['FEEDBACK_SENDER_PASSWD'])
            data = dict(
                first_name=self.user.first_name,
                last_name=self.user.last_name,
                fbid=self.user.fbid,
                text=event.message_text.strip()
            )
            body = CONFIG['FEEDBACK_BODY'].format(**data)
            g.send(dest=CONFIG['FEEDBACK_DEST'],
                   subj=CONFIG['FEEDBACK_SUBJ'],
                   body=body)
            self.set_state('Root')
        else:
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
        channels = DCRS.Channels.find(owner_uid=self.user.oid)
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
        subs = DCRS.Channels.all_subscribed(uid=self.user.oid)
        if not len(subs):
            ctas = [CTA(sid='SID_ADD_SUBSCRIPTION', action_id='AddSub')]
            self.send_simple('SID_1ST_SUBSCRIPTION_PROMPT', ctas=ctas)
        else:
            self.send_simple('SID_SUBSCRIPTIONS_PROMPT',
                             std_quick_replies=False)
            channels = DCRS.Channels.all_subscribed(uid=self.user.oid)
            ctas = [
                CTA(sid='SID_VIEW_SUB_BTN', action_id='ViewChannel'),
                CTA(sid='SID_DEL_SUB_BTN', action_id='DelSub'),
                CTA(sid='SID_SHARE_SUB_BTN', action_id='SelectShareChannelType'),
            ]
            self._state_init_select_channel(channels=channels, ctas=ctas)
            self.send_simple('SID_SUBSCRIPTION_ADD_PROMPT',
                             std_quick_replies=False)

    @BaseStateMachine.state_handler('MySubscriptions')
    def state_handler_my_subscriptions(self, event):
        if self._state_handler_add_sub(event=event):
            self.set_state('ViewChannel')
        else:
            self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('MakeAnnouncement')
    def state_init_make_annc(self):
        channels = DCRS.Channels.find(owner_uid=self.user.oid)
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
        self.send_simple('SID_GET_CHANNEL_NAME_PROMPT',
                         std_quick_replies=False)

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
        self.send_simple('SID_GET_CHANNEL_DESC_PROMPT',
                         std_quick_replies=False)

    @BaseStateMachine.state_handler('SetChannelDesc')
    def state_handler_set_channel_desc(self, event):
        assert self.channel
        if self._state_handler_edit_channel_field(fname='desc', event=event):
            logging.debug("[U#%s] Desired %s channel desc is: %s",
                          event.sender_id, self.channel.oid, self.channel.desc)
            self.set_state('ChannelCreated')
        else:
            self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('ChannelCreated')
    def state_init_channel_created(self):
        assert self.channel
        ctas = [
            CTA(sid='SID_ADD', action_id='SetChannelPic'),
            CTA(sid='SID_DONE', action_id='PostChannelCreated'),
        ]
        self.send_simple('SID_CHANNEL_CREATED', ctas=ctas)

    @BaseStateMachine.state_handler('ChannelCreated')
    def state_handler_channel_created(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('SetChannelPic')
    def state_init_set_channel_pic(self):
        assert self.channel
        self.send_simple('SID_GET_CHANNEL_PIC_PROMPT',
                         std_quick_replies=False)

    @BaseStateMachine.state_handler('SetChannelPic')
    def state_handler_set_channel_pic(self, event):
        if event.is_attachment_message:
            for a in event.message_attachments:
                if a['type'] == 'image':
                    self.channel.set_cover_pic(a['payload']['url'])
                    self.set_state('PostChannelCreated')
                    return
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('PostChannelCreated')
    def state_init_post_channel_created(self):
        assert self.channel
        ctas = [
            CTA(sid='SID_MAKE_ANNOUNCEMENT', action_id='MakeAnnc'),
        ]
        self.send_simple('SID_POST_CHANNEL_CREATED_PROMPT', ctas=ctas)

    @BaseStateMachine.state_handler('PostChannelCreated')
    def state_handler_post_channel_created(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('BrowseChannels')
    def state_init_browse_channels(self):
        channels = DCRS.Channels.find(owner_uid=self.user.oid)
        ctas = [
            CTA(sid='SID_VIEW_CHANNEL_BTN', action_id='ViewChannel'),
            CTA(sid='SID_EDIT_CHANNEL_BTN', action_id='SelectEditChannelType'),
            CTA(sid='SID_SHARE_CHANNEL_BTN', action_id='SelectShareChannelType'),
        ]
        self._state_init_select_channel(channels=channels, ctas=ctas)

    @BaseStateMachine.state_handler('BrowseChannels')
    def state_handler_browse_channels(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('ViewChannel')
    def state_init_view_channel(self):
        self._state_init_show_anncs()

    @BaseStateMachine.state_handler('ViewChannel')
    def state_handler_view_channel(self, event):
        self._state_handle_show_anncs(event=event)

    @BaseStateMachine.state_initiator('SelectEditChannelType')
    def state_init_select_edit_channel_type(self):
        ctas = [
            CTA(sid='SID_EDIT_CHANNEL_INFO', action_id='EditChannelInfo'),
            CTA(sid='SID_EDIT_CHANNEL_PIC', action_id='EditChannelPic'),
            CTA(sid='SID_DELETE_CHANNEL', action_id='DeleteChannel'),
        ]
        self.send_simple('SID_SELECT_CHANNEL_EDIT_ACTION_PROMPT', ctas=ctas)

    @BaseStateMachine.state_handler('SelectEditChannelType')
    def state_handler_select_edit_channel_type(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('EditChannelInfo')
    def state_init_edit_channel_info(self):
        self.send_simple('SID_EDIT_CHANNEL_INFO_PROMPT',
                         std_quick_replies=False)

    @BaseStateMachine.state_handler('EditChannelInfo')
    def state_handler_edit_channel_info(self, event):
        if self._state_handler_edit_channel_field(fname='name',
                                                  event=event,
                                                  skip_val='skip'):
            self.set_state('EditChannelDesc')
        else:
            self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('SelectShareChannelType')
    def state_init_select_share_channel_type(self):
        self.send_simple('SID_SELECT_CHANNEL_SHARE_ACTION_PROMPT')
        self.page.send(self.user.fbid,
                       m_link(BotRef(sub=self.channel.uchid).ref))
        self._state_init_select_share_channel_type()

    @BaseStateMachine.state_handler('SelectShareChannelType')
    def state_handler_select_share_channel_type(self, event):
        self._state_handler_select_share_channel_type(event=event)

    @BaseStateMachine.state_initiator('EditChannelDesc')
    def state_init_edit_channel_name(self):
        self.send_simple('SID_EDIT_CHANNEL_DESC_PROMPT',
                         std_quick_replies=False)

    @BaseStateMachine.state_handler('EditChannelDesc')
    def state_handler_edit_channel_name(self, event):
        if self._state_handler_edit_channel_field(fname='desc',
                                                  event=event,
                                                  skip_val='skip'):
            self.set_state('Root')
        else:
            self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('EditChannelPic')
    def state_init_edit_channel_pic(self):
        assert self.channel
        self.send_simple('SID_GET_CHANNEL_PIC_PROMPT',
                         std_quick_replies=False)

    @BaseStateMachine.state_handler('EditChannelPic')
    def state_handler_edit_channel_pic(self, event):
        if event.is_attachment_message:
            for a in event.message_attachments:
                if a['type'] == 'image':
                    self.channel.set_cover_pic(a['payload']['url'])
                    self.set_state('Root')
                    return
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
        if event.is_postback:
            p = Payload.from_string(event.postback_payload)
            if p.action_id == 'YesPseudoChatState':
                self.channel.delete()
                self.channel = None
                self.send_simple('SID_CHANNEL_REMOVED')
            else:
                self.send_simple('SID_CHANNEL_UNCHANGED')
            self.set_state('Root')
        else:
             self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('AddSub')
    def state_init_add_sub(self):
        self.send_simple('SID_ENTER_CHANNEL_ID_PROMPT',
                         std_quick_replies=False)

    @BaseStateMachine.state_handler('AddSub')
    def state_handler_add_sub(self, event):
        if self._state_handler_add_sub(event=event):
            self.set_state('ViewChannel')
        else:
            self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('DelSub')
    def state_init_del_sub(self):
        ctas = [
            CTA(sid='SID_YES', action_id='YesPseudoChatState'),
            CTA(sid='SID_NO', action_id='NoPseudoChatState')
        ]
        self.send_simple('SID_SUB_UNSUBSCRIBE_PROMPT', ctas)

    @BaseStateMachine.state_handler('DelSub')
    def state_handler_del_sub(self, event):
        if event.is_postback:
            p = Payload.from_string(event.postback_payload)
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
        channels = DCRS.Channels.find(owner_uid=self.user.oid)
        ctas = [
            CTA(sid='SID_SELECT_THIS', action_id='MakeAnnc'),
        ]
        self._state_init_select_channel(channels=channels, ctas=ctas)

    @BaseStateMachine.state_handler('AnncSelectChannel')
    def state_handler_annc_select_channel(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('MakeAnnc')
    def state_init_make_annc(self):
        self.send_simple('SID_ANNC_GET_TITLE_PROMPT', std_quick_replies=False)

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
        self.send_simple('SID_ANNC_GET_TEXT_PROMPT', std_quick_replies=False)

    @BaseStateMachine.state_handler('SetAnncText')
    def state_handler_set_annc_text(self, event):
        if event.is_text_message:
            self.annc.update(op=UpdateOps.Supported.SET,
                             text=event.message_text.strip())
            h = Horn(self.page)
            h.notify_one(user=self.user, annc=self.annc)
            h.notify(self.annc)
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
            c = DCRS.Channels.find_unique(
                uchid=r.params[self.REF_SUBSCRIBE_ACTION])
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
