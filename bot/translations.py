from enum import Enum, unique
from bot.db_datastore import BasicEntry, BasicTable


class AutoNumber(Enum):
    def __new__(cls):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    @classmethod
    def from_sid_name(cls, sid_name):
        try:
            return cls[sid_name]
        except KeyError:
            return None

    @classmethod
    def is_valid(cls, sid):
        if isinstance(sid, cls):
            return True
        if isinstance(sid, str):
            return True if cls.from_sid_name(sid) else False
        return False

    @classmethod
    def check_default_strings(cls):
        for sid in cls:
            if sid.name not in DefaultStrings:
                raise ValueError(
                    '{} must be in DefaultStrings'.format(sid.name))


    @classmethod
    def default_strings_to_db(cls, override=False):
        for sid in cls:
            s = String(sid)
            if not s.in_db or override:
                s.set(String.DEFAULT_LOCALE, DefaultStrings[sid.name])
                s.save()


class StringId(AutoNumber):
    SID_GREETING = ()
    SID_MENU_CHANNELS = ()
    SID_MENU_ANNOUNCEMENTS = ()
    SID_MENU_HELP = ()
    SID_DBG_NO_ACTION = ()
    SID_MY_CHANNELS = ()
    SID_SUBSCRIBE = ()
    SID_UNSUBSCRIBE = ()
    SID_ROOT_PROMPT = ()
    SID_BROWSE_CHANNELS = ()
    SID_MAKE_ANNOUNCEMENT = ()
    SID_BROWSE_CHANNELS_PROMPT = ()
    SID_BROWSE_NEWS_CHANNELS = ()
    SID_BROWSE_ENTERTAINMENT_CHANNELS = ()
    SID_BROWSE_SPORT_CHANNELS = ()
    SID_BROWSE_CULTURE_CHANNELS = ()
    SID_BROWSE_LOCAL_CHANNELS = ()
    SID_CREATE_CHANNEL = ()
    SID_EDIT_CHANNEL = ()
    SID_LIST_MY_CHANNELS = ()
    SID_MY_CHANNELS_PROMPT = ()
    SID_CHANNELS_HELP = ()
    SID_CHANNELS_PROMPT = ()
    SID_HELP_CHANNEL_DETAILS = ()
    SID_HELP_CHANNEL_EXAMPLES = ()
    SID_HELP_CHANNELS_PROMPT = ()


DefaultStrings = dict(
    SID_GREETING='Hi {{user_first_name}}, welcome to Locano Chatbot',
    SID_MENU_CHANNELS='Channels',
    SID_MENU_ANNOUNCEMENTS='Make an Announcement',
    SID_MENU_HELP='How To',
    SID_DBG_NO_ACTION='[DBG] Not Implemented Yet',
    SID_MY_CHANNELS='My Channels',
    SID_SUBSCRIBE='Subscribe',
    SID_UNSUBSCRIBE='Unsubscribe',
    SID_ROOT_PROMPT=('Hi! Welcome to Locano Bot. '
                     'We do information channels. You can create yours '
                     'or subscribe to someones else\'s. Try these commands:'),
    SID_BROWSE_CHANNELS='Browse Channels',
    SID_MAKE_ANNOUNCEMENT='Make an Announcement',
    SID_BROWSE_CHANNELS_PROMPT='Please choose a subject you are interested in',
    SID_BROWSE_NEWS_CHANNELS='News',
    SID_BROWSE_ENTERTAINMENT_CHANNELS='Entertainment',
    SID_BROWSE_SPORT_CHANNELS='Sport',
    SID_BROWSE_CULTURE_CHANNELS='Culture',
    SID_BROWSE_LOCAL_CHANNELS='Local',
    SID_CREATE_CHANNEL='Create Channel',
    SID_EDIT_CHANNEL='Edit Channel',
    SID_LIST_MY_CHANNELS='List My Channels',
    SID_MY_CHANNELS_PROMPT='What do you want to do next?',
    SID_CHANNELS_HELP='Channels Help',
    SID_CHANNELS_PROMPT='What do you want to do next?',
    SID_HELP_CHANNEL_DETAILS='More',
    SID_HELP_CHANNEL_EXAMPLES='Examples',
    SID_HELP_CHANNELS_PROMPT=('Channels are used to broadcast announcements. '
                              'Announcements arrive to all the Channel Subscribers')
)


class Strings(BasicTable):
    def __init__(self):
        super().__init__(kind="Strings")

    def by_sid(self, sid):
        results = self.simple_query(sid=sid)
        if len(results) > 1:
            raise ValueError("String ID must be unique")
        return results[0] if len(results) else None


class String(BasicEntry):
    table = Strings()
    LOCALE_MARKER = 'locale'
    LOCALE_DELIMITER = '.'
    DEFAULT_LOCALE = 'en_US'

    @classmethod
    def locale_aname(cls, locale):
        return cls.LOCALE_MARKER + cls.LOCALE_DELIMITER + locale

    @classmethod
    def locale_by_aname(cls, aname):
        t = aname.split(cls.LOCALE_DELIMITER)
        if len(t) == 2 and t[0] == cls.LOCALE_MARKER:
            return t[1]
        return None

    @classmethod
    def all(cls):
        l = []
        results = String.table.simple_query()
        for e in results:
            s = String()
            s.from_entity(e)
            l.append(s)
        return l

    def __init__(self, sid=None):
        super().__init__(self.table)
        self.add_db_field('sid', '')
        if sid:
            self.load(sid)

    @property
    def in_db(self):
        return self.oid is not None

    def load(self, sid):
        ssid = sid.name if isinstance(sid, StringId) else sid
        e = self.table.by_sid(ssid)
        if e:
            self.from_entity(e)
            return True
        self.sid = ssid
        return False

    def set(self, locale, text):
        self.add_db_field(self.locale_aname(locale), text)

    def get(self, locale):
        try:
            return getattr(self, self.locale_aname(locale))
        except AttributeError:
            return None

    def get_safe(self, locale):
        if locale:
            s = self.get(locale) # get from locale
            if s:
                return s

        if not locale or locale != self.DEFAULT_LOCALE:
            s = self.get(self.DEFAULT_LOCALE)  # get from default locale
            if s:
                return s

        return DefaultStrings[self.sid]  # get default

    def list(self):
        l = []
        for key in self.db_fields:
            locale = self.locale_by_aname(key)
            if locale:
                l.append(locale)
        return l


class BotString(String):
    def __init__(self, sid, locale=None):
        super().__init__(sid)
        self.locale = locale

    @property
    def string(self):
        return self.get_safe(self.locale)

    def __str__(self):
        return self.get_safe(self.locale)
