import logging
from abc import ABC, abstractmethod
from enum import Enum
from fbmq import QuickReply
from bot.db_datastore import BasicEntry, BasicTable


CHAT_CLB_ID = 'CHAT_CLB'
START_ACTION = 'Start'

class ChatTable(BasicTable):
    def __init__(self):
        super().__init__(kind="Chats")

    def by_fbid(self, fbid):
        return self.simple_query(fbid=fbid)

class BaseChat(BasicEntry):
    chats = ChatTable()
    subs = {}

    @classmethod
    def addsub(cls, scls):
        cls.subs[scls.__name__] = scls
        return scls

    @classmethod
    def by_db_entity(cls, page, entity):
        i = cls.subs[entity['class_name']](page)
        i.from_entity(entity)
        return i

    @classmethod
    def by_fbid(cls, page, fbid):
        results = cls.chats.simple_query(fbid=fbid)
        if results:
            if len(results) > 1:
                raise ValueError("FB ID must be unique")
        return cls.by_db_entity(page, results[0])

    @classmethod
    def by_oid(cls, page, oid):
        i = None
        entity = cls.chats.read(oid)
        if entity:
            i = cls.by_db_entity(page, entity)
        else:
            logging.warning("from_db: cannot find dbs for id=%s", oid)
        return i

    @classmethod
    def from_db(cls, page, payload):
        i = None
        is_ok, class_name, oid, action_id = cls.parse_callback_payload(payload)
        if is_ok:
            i = cls.by_oid(page, oid)
        else:
            logging.warning("from_db: incorrect payload: %s", payload)
        return i, action_id

    def format_callback_payload(self, action_id):
        return CHAT_CLB_ID + '/' + self.class_name + '/' + str(self.oid) + '/' + str(action_id)

    @staticmethod
    def parse_callback_payload(payload):
        params = payload.split('/')
        is_ok = False
        class_name = None
        oid = None
        action_id = None
        if params[0] == CHAT_CLB_ID and len(params) == 4:
            is_ok = True
            class_name = params[1]
            oid = params[2]
            action_id = params[3]
        return is_ok, class_name, oid, action_id

    @classmethod
    def cleanup(cls, fbid):
        entities = cls.chats.by_fbid(fbid)
        for e in entities:
            cls.chats.delete(e.key.id)

    @property
    def class_name(self):
        return type(self).__name__

    def __init__(self, page, fbid=None):
        super().__init__(self.chats)
        self.page = page
        self.add_db_field('fbid', fbid)
        self.add_db_property('class_name')
        if fbid:
            self.cleanup(fbid)

    def start(self):
        if not self.oid:
            self.save()
        self.on_user_action(START_ACTION, None)

    @abstractmethod
    def on_user_action(self, action_id, event):
        pass


@BaseChat.addsub
class SelectChannelActionChat(BaseChat):
    start_actions = dict(
        ChList = 'List My Channels',
        ChSub = 'Subscribe',
        ChUnSub = 'Unsubscribe',
        ChCancel = 'Cancel'
    )

    def on_action_start(self):
        quick_replies = []
        for k, v in type(self).start_actions.items():
            quick_replies.append(QuickReply(title=v, payload=self.format_callback_payload(k)))
        self.page.send(self.fbid,
                       "What do you want to do next?",
                       quick_replies=quick_replies,
                       metadata="DEVELOPER_DEFINED_METADATA")
        self.save()

    def on_user_action(self, action_id, event):
        if action_id == START_ACTION:
            self.on_action_start()
        else:
            logging.warning("on_user_action: %s arrived", action_id)


def chat_clb_handler(page, payload, event):
    instance, action_id = BaseChat.from_db(page, payload)
    if instance:
        instance.on_user_action(action_id, event)
