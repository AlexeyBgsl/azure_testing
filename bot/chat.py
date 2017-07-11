import logging
from datetime import datetime
from abc import ABC, abstractmethod
from enum import Enum
from fbmq import QuickReply
from bot.db_datastore import Chat, Chats


CHAT_CLB_ID = 'CHAT_CLB'
START_ACTION = 'Start'

class BaseChat(ABC):
    chats = Chats()

    @classmethod
    def from_db(cls, payload):
        instance = None
        is_ok, class_name, oid, action_id = cls.parse_callback_payload(payload)
        if is_ok:
            dbs = cls.chats.read(oid)
            if dbs:
                instance = classdict[class_name](dbs)
            else:
                logging.warning("from_db: cannot find dbs for id=%d", oid)
        else:
            logging.warning("from_db: incorrect payload: %s", payload)
        return instance, action_id

    def format_callback_payload(self, action_id):
        return CHAT_CLB_ID + '/' + self.class_name() + '/' + str(self.dbs.id) + '/' + str(action_id)

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

    def __init__(self, page, fbid=None, dbs=None):
        self.page = page
        self.fbid = fbid
        self.dbs = dbs

    def start(self):
        if not self.dbs:
            self.to_db()
        else:
            self.fbid = self.dbs.entry['fbid']
        self.on_user_action(START_ACTION, None)

    def to_dict(self):
        return dict(cls = self.class_name(),
                    fbid = self.fbid,
                    timestamp = datetime.utcnow())

    def to_db(self):
        d = self.to_dict()
        if not self.dbs:
            self.dbs = Chat.create(self.chats, d)
        else:
            self.dbs.update(d)

    @classmethod
    def class_name(cls):
        return cls.__name__

    @abstractmethod
    def on_user_action(self, action_id, event):
        pass


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


    def on_user_action(self, action_id, event):
        if action_id == START_ACTION:
            self.on_action_start()
        else:
            logging.warning("on_user_action: %s arrived", action_id)


classdict = {
    'SelectChannelActionChat': SelectChannelActionChat
    }


def chat_clb_handler(page, payload, event):
    instance, action_id = BaseChat.from_db(payload)
    instance.on_user_action(action_id, event)
