from bot.db_datastore import BasicEntry, BasicTable
from string import Template


def default_strings_to_db(override=False):
    for sid in DefaultStrings:
        s = String(sid)
        if not s.in_db or override:
            s.set(String.DEFAULT_LOCALE, DefaultStrings[sid])
            s.save()


DefaultStrings = dict(
    SID_YES='Yes',
    SID_NO='No',
    SID_GREETING='Hi {{user_first_name}}, welcome to Locano Chatbot',
    SID_DONT_UNDERSTAND='Sorry, I don\'t understand you',
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
    SID_IDLE_PROMPT='What do you want to do next?',
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
    SID_HELP_CHANNELS_PROMPT=('Channels are used to broadcast announcements.\n'
                              'Announcements arrive to all the Channel Subscribers'),
    SID_GET_CHANNEL_NAME='Enter desired channel name',
    SID_GET_CHANNEL_DESC=('Channel $CHANNEL_NAME created.\n'
                          'Channel ID is $CHANNEL_ID.\n'
                          'Enter channel description'),
    SID_CHANNEL_CREATED='Channel $CHANNEL_NAME ($CHANNEL_ID) is ready to use',
    SID_SELECT_CHANNEL_PROMPT=('Please select a desired Channel from list '
                               'or enter Channel ID'),
    SID_SELECT_CHANNEL_EDIT_ACTION='What do you want to do with channel $CHANNEL_NAME?',
    SID_EDIT_CHANNEL_NAME='Change Name',
    SID_EDIT_CHANNEL_DESC='Change Description',
    SID_EDIT_CHANNEL_DELETE='Delete Channel',
    SID_EDIT_CHANNEL_NAME_PROMPT='Please enter new Channel Name',
    SID_CHANNEL_NAME_CHANGED='Channel $CHANNEL_ID name changed successfully',
    SID_EDIT_CHANNEL_DESC_PROMPT='Please enter new Channel Description',
    SID_CHANNEL_DESC_CHANGED='Channel $CHANNEL_NAME description changed successfully',
    SID_DEL_CHANNEL_PROMPT='Are you sure?',
    SID_CHANNEL_REMOVED="Channel successfully removed",
    SID_CHANNEL_UNCHANGED="Channel remains unchanged",
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

    @classmethod
    def all_defaults(cls):
        return list(DefaultStrings.keys())

    def __init__(self, sid=None):
        super().__init__(self.table)
        self.add_db_field('sid', '')
        if sid:
            self.load(sid)

    @property
    def in_db(self):
        return self.oid is not None

    @property
    def has_def(self):
        return self.sid in DefaultStrings

    def load(self, sid):
        e = self.table.by_sid(sid)
        if e:
            self.from_entity(e)
            return True
        self.sid = sid
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
    SUB_USER_FIRST_NAME='USER_FIRST_NAME'
    SUB_USER_LAST_NAME='USER_LAST_NAME'
    SUB_CHANNEL_NAME='CHANNEL_NAME'
    SUB_CHANNEL_ID='CHANNEL_ID'

    def __init__(self, sid, locale=None, user=None, channel=None):
        super().__init__(sid)
        self.locale = locale
        self.user = user
        self.channel = channel

    def __str__(self):
        d = {}
        if self.user:
            d[self.SUB_USER_FIRST_NAME] = self.user.first_name
            d[self.SUB_USER_LAST_NAME] = self.user.last_name
        if self.channel:
            d[self.SUB_CHANNEL_NAME] = self.channel.name
            d[self.SUB_CHANNEL_ID] = self.channel.str_chid
        return Template(self.get_safe(self.locale)).safe_substitute(d)
