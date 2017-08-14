import logging
from fbmq import QuickReply, Template
from bot.translations import BotString
from db import Channel, Annc, UpdateOps
from bot.horn import Horn


BotChatClbTypes = dict(
    ClbQRep="CHAT_CLB_QREP",
    ClbMenu="CHAT_CLB_MENU",
    ClbMsg="CHAT_CLB_MSG"
)


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


class CTAList(object):
    class CTA(object):
        def __init__(self, sid, action_id):
            self.sid = sid
            self.action_id = action_id

    def __init__(self, sm, **kwargs):
        self.ctas = []
        self.sm = sm
        self.add(**kwargs)

    def add(self, **kwargs):
        for k in kwargs:
            self.ctas.append(CTAList.CTA(sid=k, action_id=kwargs[k]))

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

    class ChannelSelector(object):
        MAX_LIST_ITEMS = 4
        CHAN_ACTION_ID = 'Select'

        @classmethod
        def get_next_skip(cls, p):
            return int(p.action_id) if p.action_id != cls.CHAN_ACTION_ID else None

        @classmethod
        def get_selected_channel(cls, p):
            return p.channel

        def __init__(self, state, channels=None, skip=None):
            assert not channels or isinstance(channels, list)
            assert not skip or isinstance(skip, int)
            self.state = state
            self.channels = channels if channels else []
            self.skip = skip if skip else 0

        @property
        def is_done(self):
            return len(self.channels) == self.skip

        def next_message(self):
            if self.is_done:
                return None
            nof_channels = len(self.channels)
            max = self.skip + self.MAX_LIST_ITEMS
            if nof_channels < max:
                max = nof_channels
            elements = []
            for c in self.channels[self.skip:max]:
                btn = \
                    Template.ButtonPostBack("Select",
                                            str(Payload(type='ClbQRep',
                                                        state=self.state,
                                                        action_id=self.CHAN_ACTION_ID,
                                                        channel=c)))

                elements.append(Template.GenericElement(c.name,
                                                        subtitle=c.str_uchid + '\n' + c.desc,
                                                        image_url=c.qr_code,
                                                        buttons=[btn]))
            buttons = None
            if max != nof_channels:
                buttons = [
                    Template.ButtonPostBack("Next",
                                            str(Payload(type='ClbQRep',
                                                        state=self.state,
                                                        action_id=str(max))))
                ]

            self.skip = max
            if len(elements) == 1:
                return Template.Generic(elements)
            else:
                return Template.GenericList(elements,
                                            top_element_style='compact',
                                            buttons=buttons)

    @classmethod
    def class_name(cls):
        return cls.__name__

    def _register_for_user_input(self):
        p = Payload(type='ClbMsg', state=self.state, action_id='UsrInput',
                    channel=self.channel, annc=self.annc)
        self.page.register_for_message(self.user, str(p))

    def set_state(self, state):
        if state != self.state:
            super().set_state(state=state)
            self._register_for_user_input()

    def send_simple(self, msg_sid, ctas = None):
        msg = str(BotString(msg_sid, user=self.user, channel=self.channel))
        qreps = ctas.quick_replies if ctas else None
        self.page.send(self.user.fbid, msg, quick_replies=qreps)

    def on_qrep_simple(self, **kwargs):
        action_id = kwargs.get('action_id', 'Root')
        self.set_state(action_id)

    def _state_init_select_channel(self, subscribed):
        if subscribed:
            channels = Channel.all_subscribed(uid=self.user.oid)
            msg_sid = 'SID_SELECT_SUB_PROMPT'
        else:
            channels = Channel.find(owner_uid=self.user.oid)
            msg_sid = 'SID_SELECT_CHANNEL_PROMPT'
        selector = self.ChannelSelector(state=self.state,
                                        channels=channels,
                                        skip=getattr(self, 'skip', 0))
        self.page.send(self.user.fbid, selector.next_message())

    def _state_handle_select_channel(self, event):
        if not event.is_postback:
            return False
        p = Payload.from_string(event.postback_payload)
        self.channel = self.ChannelSelector.get_selected_channel(p)
        if self.channel:
            return True
        skip = self.ChannelSelector.get_next_skip(p)
        if skip:
            setattr(self, 'skip', skip)
            return True
        return False

    def _state_handler_edit_channel_field(self, fname, event):
        if not event.is_text_message:
            return False
        val = event.message_text.strip()
        setattr(self.channel, fname, val)
        self.channel.update_db(op=UpdateOps.Supported.SET,
                               val={fname: val})
        return True

    def _state_handler_default(self, event):
        if event.is_quick_reply:
            p = Payload.from_string(event.quick_reply_payload)
            self.set_state(p.action_id)
        elif event.is_postback:
            p = Payload.from_string(event.postback_payload)
            self.set_state(p.action_id)
        elif event.is_text_message:
            pass
        else:
            pass

    @BaseStateMachine.state_initiator('Root')
    def state_init_root(self):
        ctas = CTAList(sm=self,
                       SID_BROWSE_CHANNELS='BrowseChannels',
                       SID_MY_CHANNELS='MyChannels',
                       SID_MY_SUBSCRIPTIONS='MySubscriptions',
                       SID_MAKE_ANNOUNCEMENT='MakeAnnouncement')
        self.send_simple('SID_ROOT_PROMPT', ctas)

    @BaseStateMachine.state_handler('Root')
    def state_handler_root(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('Channels')
    def state_init_channels(self):
        ctas = CTAList(sm=self,
                       SID_BROWSE_CHANNELS='BrowseChannels',
                       SID_MY_CHANNELS='MyChannels',
                       SID_CHANNELS_HELP='ChannelsHelp')
        self.send_simple('SID_CHANNELS_PROMPT', ctas)

    @BaseStateMachine.state_initiator('BrowseChannels')
    def state_init_browse_channels(self):
        ctas = CTAList(sm=self,
                       SID_BROWSE_NEWS_CHANNELS='Root',
                       SID_BROWSE_ENTERTAINMENT_CHANNELS='Root',
                       SID_BROWSE_SPORT_CHANNELS='Root',
                       SID_BROWSE_CULTURE_CHANNELS='Root',
                       SID_BROWSE_LOCAL_CHANNELS='Root')
        self.send_simple('SID_BROWSE_CHANNELS_PROMPT', ctas)

    @BaseStateMachine.state_handler('BrowseChannels')
    def state_handler_browse_channels(self, event):
        self.send_simple('SID_DBG_NO_ACTION')
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('MyChannels')
    def state_init_my_channels(self):
        channels = Channel.find(owner_uid=self.user.oid)
        ctas = CTAList(sm=self,
                       SID_CREATE_CHANNEL='CreateChannel')
        if len(channels):
            ctas.add(SID_EDIT_CHANNEL='EditChannel')
        self.send_simple('SID_MY_CHANNELS_PROMPT', ctas)

    @BaseStateMachine.state_handler('MyChannels')
    def state_handle_my_channels(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('ChannelsHelp')
    def state_init_channels_help(self):
        self.send_simple('SID_DBG_NO_ACTION')

    @BaseStateMachine.state_handler('ChannelsHelp')
    def state_handler_channels_help(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('MySubscriptions')
    def state_init_my_subscriptions(self):
        subs = Channel.all_subscribed(self.user.oid)
        ctas = CTAList(sm=self,
                       SID_ADD_SUBSCRIPTION='AddSub')
        if len(subs):
            ctas.add(SID_LIST_SUBSCRIPTIONS='ListSubs')
        self.send_simple('SID_SUBSCRIPTIONS_PROMPT', ctas)

    @BaseStateMachine.state_handler('MySubscriptions')
    def state_handler_my_subscriptions(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('MakeAnnouncement')
    def state_init_make_annc(self):
        channels = Channel.find(owner_uid=self.user.oid)
        ctas = CTAList(sm=self,
                       SID_ANNC_NEW_CHANNEL='CreateChannel')
        if len(channels):
            ctas.add(SID_ANNC_SELECT_CHANNEL='AnncSelectChannel')
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
        pass

    @BaseStateMachine.state_handler('SetChannelDesc')
    def state_handler_set_channel_desc(self, event):
        assert self.channel
        if event.is_text_message:
            logging.debug("[U#%s] Desired %s channel desc is: %s",
                          event.sender_id, self.channel.oid, event.message_text)
            self.channel.desc = event.message_text
            self.channel.update_db(op=UpdateOps.Supported.SET,
                                   val={'desc': self.channel.desc})
            self.send_simple('SID_CHANNEL_CREATED')
            self.set_state('Root')
        else:
            self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('EditChannel')
    def state_init_edit_channel(self):
        self._state_init_select_channel(subscribed=False)

    @BaseStateMachine.state_handler('EditChannel')
    def state_handler_edit_channel(self, event):
        if self._state_handle_select_channel(event=event):
            if self.channel:
                self.set_state('SelectEditChannelType')
        else:
            self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('SelectEditChannelType')
    def state_init_select_edit_channel_type(self):
        ctas = CTAList(sm=self,
                       SID_EDIT_CHANNEL_NAME='EditChannelName',
                       SID_EDIT_CHANNEL_DESC='EditChannelDesc',
                       SID_EDIT_CHANNEL_DELETE='DeleteChannel')
        self.send_simple('SID_SELECT_CHANNEL_EDIT_ACTION', ctas)

    @BaseStateMachine.state_handler('SelectEditChannelType')
    def state_handler_select_edit_channel_type(self, event):
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
        ctas = CTAList(sm=self,
                       SID_YES='YesPseudoChatState',
                       SID_NO='NoPseudoChatState')
        self.send_simple('SID_DEL_CHANNEL_PROMPT', ctas)

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
        self._state_init_select_channel(subscribed=True)

    @BaseStateMachine.state_handler('ListSubs')
    def state_handler_list_subs(self, event):
        if self._state_handle_select_channel(event=event):
            if self.channel:
                self.set_state('SubSelectAction')
        else:
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

    @BaseStateMachine.state_initiator('SubSelectAction')
    def state_init_sub_select_action(self):
        ctas = CTAList(sm=self,
                       SID_SUB_DELETE='DelSub',
                       SID_SUB_SHOW_ANNCS='Root')
        self.send_simple('SID_SELECT_SUB_ACTION_PROMPT', ctas)

    @BaseStateMachine.state_handler('SubSelectAction')
    def state_handler_sub_select_action(self, event):
        self._state_handler_default(event=event)

    @BaseStateMachine.state_initiator('DelSub')
    def state_init_del_sub(self):
        ctas = CTAList(sm=self,
                       SID_YES='YesPseudoChatState',
                       SID_NO='NoPseudoChatState')
        self.send_simple('SID_SUB_UNSUBSCRIBE_PROMPT', ctas)

    @BaseStateMachine.state_handler('DelSubs')
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
        self._state_init_select_channel(subscribed=False)

    @BaseStateMachine.state_handler('AnncSelectChannel')
    def state_handler_annc_select_channel(self, event):
        if self._state_handle_select_channel(event=event):
            if self.channel:
                self.set_state('MakeAnnc')
        else:
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
            self.annc.text = event.message_text.strip()
            self.annc.update_db(op=UpdateOps.Supported.SET,
                                val={'text': self.annc.text})
            self.send_simple('SID_ANNC_DONE')
            self.annc = None
            self.set_state('Root')
            Horn(self.page).notify(self.annc)
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
        menu_items = dict(
            SID_MENU_ANNOUNCEMENTS='MakeAnnouncement',
            SID_MENU_CHANNELS='MyChannels',
            SID_MENU_SUBSCRIPTIONS='MySubscriptions',
            SID_MENU_HELP='Help'
        )
        buttons = []
        for k in menu_items:
            p = Payload(type='ClbMenu', state='Root', action_id=menu_items[k])
            btn = Template.ButtonPostBack(str(BotString(k)), str(p))
            buttons.append(btn)
        return buttons

    def _on_menu(self, event):
        self._state_handler_default(event=event)

    def __init__(self, page, user, state='Root', channel=None, annc=None):
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


def chat_msg_handler(user, page, payload, event):
    logging.debug("[U#%s] Msg Handler: %s", event.sender_id, payload)
    BotChat.clb_by_payload(user, page, payload, event)
