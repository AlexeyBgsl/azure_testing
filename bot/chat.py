import logging
from abc import ABC, abstractmethod
from fbmq import QuickReply
from bot.db_datastore import BasicEntry, BasicTable


CHAT_CLB_ID = 'CHAT_CLB'
START_ACTION = 'Start'


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


class Hierarchy():
    DELIMITER = '.'

    def __init__(self, str):
        self.hstr = str

    @property
    def is_empty(self):
        return not self.hstr

    @property
    def nof_levels(self):
        return self.hstr.count(self.DELIMITER) + 1

    def get_current_level(self):
        pos = self.hstr.rfind(self.DELIMITER)
        return self.hstr[pos + 1:]

    def level_up(self, next_level):
        if self.is_empty:
            self.hstr = next_level
        else:
            self.hstr += self.DELIMITER + next_level

    def level_down(self):
        pos = self.hstr.rfind(self.DELIMITER)
        self.hstr = self.hstr[:pos] if pos != -1 else ''

    def __str__(self):
        return self.hstr


class CallToAction(object):
    def __init__(self, title, action_id, class_name):
        self.title = title
        self.action_id = action_id
        self.class_name = class_name


class BackCallToAction(CallToAction):
    CLS_NAME = 'BackCTAClass'
    ACTION_ID = 'BackCTAAction'

    def __init__(self, title='Back'):
        super().__init__(title, self.ACTION_ID, self.CLS_NAME)


class NoCallToAction(CallToAction):
    CLS_NAME = 'NoCTAClass'
    ACTION_ID = 'NoCTAAction'

    def __init__(self, title):
        super().__init__(title, self.ACTION_ID, self.CLS_NAME)


class BasicChatStep(ABC):
    CTA = []

    @classmethod
    def name(cls):
        return cls.__name__

    @classmethod
    def on_action_done(cls, cta, event):
        pass

    @classmethod
    def on_action(cls, action_id, event):
        logging.debug("%s: on_action: %s arrived", cls.name(), action_id)
        for cta in cls.CTA:
            if cta.action_id == action_id:
                cls.on_action_done(cta, event)
                logging.debug("%s: next CTA: %s", cls.name(), cta.class_name)
                return cta.class_name
        return None


class ChatTable(BasicTable):
    def __init__(self):
        super().__init__(kind="Chats")

    def by_fbid(self, fbid):
        return self.simple_query(fbid=fbid)


step_collection = ClassCollection()


@step_collection.register
class RootChatStep(BasicChatStep):
    CTA = [
        CallToAction('Channels', 'RtChls', 'FirstChannelsChatStep'),
        CallToAction('Announcements', 'RtAnns', 'FirstAnnouncementsChatStep'),
        CallToAction('Help', 'RtHelp', 'FirstHelpChatStep'),
    ]


@step_collection.register
class FirstChannelsChatStep(BasicChatStep):
    CTA = [
        NoCallToAction('List My Channels'),
        NoCallToAction('Subscribe'),
        NoCallToAction('Unsubscribe'),
        BackCallToAction()
    ]


@step_collection.register
class FirstAnnouncementsChatStep(BasicChatStep):
    pass


bot_collection = ClassCollection()


class BaseChat(BasicEntry):
    chats = ChatTable()

    @classmethod
    def by_db_entity(cls, page, entity):
        i = bot_collection.instantiate(entity['class_name'], page)
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

    def __init__(self, page, fbid=None, entity=None):
        super().__init__(self.chats, entity=entity)
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


@bot_collection.register
class BotChat(BaseChat):
    @staticmethod
    def root_menu():
        return RootChatStep.CTA

    def __init__(self, page, fbid=None, hierarchy=None):
        super().__init__(page, fbid)
        h = hierarchy if hierarchy else str(Hierarchy('RootChatStep'))
        self.add_db_field('hierarchy', h)
        logging.debug("[U#%s] bot created (h=%s)", fbid, h)

    @property
    def hobj(self):
        return Hierarchy(self.hierarchy)

    def _ask_for_cta(self, cls):
        quick_replies = []
        for c in cls.CTA:
            quick_replies.append(
                QuickReply(title=c.title,
                           payload=self.format_callback_payload(c.action_id)))
        logging.debug("[U#%s] CTAs sent: %r", self.fbid, quick_replies)
        self.page.send(self.fbid,
                       "What do you want to do next?",
                       quick_replies=quick_replies,
                       metadata="DEVELOPER_DEFINED_METADATA")

    @property
    def current_level_cls(self):
        class_name = self.hobj.get_current_level()
        return step_collection.cls(class_name)

    def start(self, action_id, event):
        self.on_user_action(action_id, event)

    def level_up(self, class_name):
        cta_cls = step_collection.cls(class_name)
        if cta_cls:
            self.hierarchy = str(self.hobj.level_up(class_name))
            self.save()
            logging.debug("[U#%s] level up: %s", self.fbid, self.hierarchy)
            self._ask_for_cta(cta_cls)

    def level_down(self):
        hobj = self.hobj
        assert hobj.nof_levels > 1, "%s: there's no level down" % str(self.hierarchy)
        self.hierarchy = str(hobj.level_down())
        self.save()
        if hobj.nof_levels > 1:
            self._ask_for_cta(self.current_level_cls)
        else:
            logging.warning("%s: cannot level down: %s", self.hierarchy)

    def on_user_action(self, action_id, event):
        if action_id == BackCallToAction.ACTION_ID:
            logging.debug("[U#%s] back action received: %s",
                          self.fbid, self.hierarchy)
            self.level_down()
        elif action_id == NoCallToAction.ACTION_ID:
            logging.debug("[U#%s] no action received: %s",
                          self.fbid, self.hierarchy)
            self._ask_for_cta(self.current_level_cls)
        else:
            cls = self.current_level_cls
            next_level_class_name = cls.on_action(action_id, event)
            logging.debug("[U#%s] %s action received: %s",
                          self.fbid, action_id, self.hierarchy)
            self.level_up(next_level_class_name)


def chat_clb_handler(page, payload, event):
    instance, action_id = BaseChat.from_db(page, payload)
    if instance:
        logging.debug("[U#%s] bot instance reconstructed: %s",
                      event.sender_id, payload)
        instance.on_user_action(action_id, event)
    else:
        logging.warning("[U#%s] cannot reconstruct bot instance: %s",
                        event.sender_id, payload)
