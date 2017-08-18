from db import String
from string import Template


DefaultStrings = dict(
    SID_YES='Yes',
    SID_NO='No',
    SID_ERROR='Something went wrong...',
    SID_GREETING='Hi {{user_first_name}}, welcome to Locano Chatbot',
    SID_DONT_UNDERSTAND='Sorry, I don\'t understand you',
    SID_MENU_CHANNELS='Channels',
    SID_MENU_SUBSCRIPTIONS='Your Subscriptions',
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
    SID_MY_SUBSCRIPTIONS='My Subscriptions',
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
    SID_LIST_SUBSCRIPTIONS="List Subscriptions",
    SID_ADD_SUBSCRIPTION="Subscribe",
    SID_DEL_SUBSCRIPTION="Unsubscribe",
    SID_SUBSCRIPTIONS_PROMPT='What do you want to do next?',
    SID_SUB_ADDED="Subscription to channel $CHANNEL_NAME added",
    SID_SUB_EXISTS="You are already subscribed to channel $CHANNEL_NAME",
    SID_ENTER_CHANNEL_ID_PROMPT="Enter desired Channel ID",
    SID_SELECT_SUB_PROMPT=('Please select a desired Subscription from list '
                           'or enter Channel ID'),
    SID_NO_SUBS_PROMPT="You have no active subscriptions",
    SID_SELECT_SUB_ACTION_PROMPT='What do you want to do next?',
    SID_SUB_DELETE='Unsubscribe',
    SID_SUB_SHOW_ANNCS='Show Announcements',
    SID_SUB_UNSUBSCRIBE_PROMPT='Are you sure?',
    SID_SUB_REMOVED="Done",
    SID_SUB_UNCHANGED="Subscription remained",
    SID_ANNC_GET_TITLE_PROMPT="Please enter the Announcement title",
    SID_ANNC_GET_TEXT_PROMPT="Please enter the Announcement text",
    SID_ANNC_DONE="Announcement Created",
    SID_ANNC_ROOT_PROMPT="Please choose channel",
    SID_ANNC_CREATE_CHANNEL_PROMPT="Please create a channel first",
    SID_ANNC_NEW_CHANNEL="New Channel",
    SID_ANNC_SELECT_CHANNEL="Select Channel",
    SID_ANNC_MESSAGE=("== Announcement Notification ==\n"
                      "Channel: $CHANNEL_NAME ($CHANNEL_ID)\n"\
                      "Title: $ANNC_TITLE\n\n"
                      "$ANNC_TEXT\n"),
    SID_SELECT_THIS="Select",
    SID_BACK="Back",
    SID_NEXT="Next",
)


class BotString(String):
    SUB_USER_FIRST_NAME='USER_FIRST_NAME'
    SUB_USER_LAST_NAME='USER_LAST_NAME'
    SUB_CHANNEL_NAME='CHANNEL_NAME'
    SUB_CHANNEL_ID='CHANNEL_ID'
    SUB_ANNC_TITLE='ANNC_TITLE'
    SUB_ANNC_TEXT='ANNC_TEXT'
    defaults = DefaultStrings

    @classmethod
    def default_strings_to_db(cls, override=False):
        for sid in cls.defaults:
            s = String(sid)
            if not s.in_db or override:
                s.set(String.DEFAULT_LOCALE, cls.defaults[sid])
                s.save()

    @classmethod
    def all_defaults(cls):
        return list(cls.defaults.keys())

    @property
    def has_def(self):
        return self.sid in self.defaults

    def __init__(self, sid, locale=None, user=None, channel=None, annc=None):
        super().__init__(sid)
        self.locale = locale
        self.user = user
        self.channel = channel
        self.annc = annc

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

    def __str__(self):
        d = {}
        if self.user:
            d[self.SUB_USER_FIRST_NAME] = self.user.first_name
            d[self.SUB_USER_LAST_NAME] = self.user.last_name
        if self.channel:
            d[self.SUB_CHANNEL_NAME] = self.channel.name
            d[self.SUB_CHANNEL_ID] = self.channel.str_uchid
        if self.annc:
            d[self.SUB_ANNC_TITLE] = self.annc.title
            d[self.SUB_ANNC_TEXT] = self.annc.text
        return Template(self.get_safe(self.locale)).safe_substitute(d)
