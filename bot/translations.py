from db import String
from string import Template


DefaultStrings = dict(
    SID_YES='Yes',
    SID_NO='No',
    SID_ERROR='Something went wrong...',
    SID_GREETING='Hi {{user_first_name}}, welcome to Locano Chatbot',
    SID_DONT_UNDERSTAND='Sorry, I don\'t understand you',
    SID_MENU_CHANNELS='Channels',
    SID_MENU_SUBSCRIPTIONS='Subscriptions',
    SID_MENU_ANNOUNCEMENTS='Make an Announcement',
    SID_MENU_HELP='How To',
    SID_DBG_NO_ACTION='[DBG] Not Implemented Yet',
    SID_ACQUAINTANCE_PROMPT=(
        'Welcome to Locano Bot. Today, having your own bot is like owning '
        'bitcoins — it’s every bit as cool. Locano Bot is an announcement '
        'service. Here you can subscribe to someone else’s information '
        'channels or create your own ones, which will only take a few simple '
        'steps. For a user to be able to subscribe to your channel, you’ll '
        'need to provide him/her with the channel’s ID which you got when '
        'creating the channel. Being based on Facebook Messenger, Locano Bot '
        'is a worldwide service available on any platform. Locano Bot is at '
        'your service:'),
    SID_FEEDBACK_PROMPT='Please send your feedback to us',
    SID_FEEDBACK_DONE=('Thanks a lot for your feedback!\n'''
                       'We\'ll study it ASAP and get back to you shortly to share '
                       'our thoughts on it.'),
    SID_HOW_TO='How To',
    SID_FEEDBACK='Feedback',
    SID_DONE='Done',
    SID_ADD='Add',
    SID_MY_CHANNELS='Channels',
    SID_SUBSCRIBE='Subscribe',
    SID_UNSUBSCRIBE='Unsubscribe',
    SID_ROOT_PROMPT='Locano Bot is at your service:',
    SID_MAKE_ANNOUNCEMENT='Make an Announcement',
    SID_CREATE_CHANNEL='Create Channel',
    SID_BROWSE_CHANNELS='Browse Channels',
    SID_MY_SUBSCRIPTIONS='Subscriptions',
    SID_MY_CHANNELS_PROMPT=(
        'Information channel is a means of delivering announcements to '
        'subscribers. Browse through your channels to share or edit them or create a '
        'new one.'),
    SID_HELP_CHANNEL_DETAILS='More',
    SID_HELP_CHANNEL_EXAMPLES='Examples',
    SID_HELP_CHANNELS_PROMPT=('Channels are used to broadcast announcements.\n'
                              'Announcements are dispatched to all the Channel Subscribers'),
    SID_GET_CHANNEL_NAME_PROMPT='Enter channel name:',
    SID_GET_CHANNEL_DESC_PROMPT='Enter channel description:',
    SID_GET_CHANNEL_PIC_PROMPT=('Send a picture that will serve as the '
                                'channel\'s cover image to us\n\n'
                                'For assistance: http://tinyurl.com/yc2r5q43'),
    SID_CHANNEL_CREATED=('Add a picture that will serve as the channel\'s '
                         'cover image or press Done'),
    SID_POST_CHANNEL_CREATED_PROMPT=('Your channel $CHANNEL_NAME has been created, '
                                     'now is the best time to make your first '
                                     'announcement:'),
    SID_SELECT_CHANNEL_EDIT_ACTION_PROMPT=(
        'Change name, description or cover image of $CHANNEL_NAME. Please '
        'note, you can skip certain steps:'),
    SID_EDIT_CHANNEL_PIC='Add a New Image',
    SID_DELETE_CHANNEL='Delete Channel',
    SID_SELECT_CHANNEL_SHARE_ACTION_PROMPT=(
        'Choose your preferred method of sharing the channel. You can also '
        'copy the URL below and share it outside the Messenger for folks to be '
        'able to subscribe to your channel anywhere.'
    ),
    SID_CHANNEL_INFO='Channel Info',
    SID_EDIT_CHANNEL_INFO='Name and Description',
    SID_EDIT_CHANNEL_INFO_PROMPT=(
        'Enter a new name. Type \'skip\' if you don\'t want to change it and '
        'only need to change the description.'
    ),
    SID_EDIT_CHANNEL_DESC_PROMPT=(
        'Enter a new description. Type \'skip\' if you don\'t want to change it.'
    ),
    SID_DEL_CHANNEL_PROMPT='Are you sure?',
    SID_CHANNEL_REMOVED="Channel successfully removed",
    SID_CHANNEL_UNCHANGED="Channel remains unchanged",
    SID_LIST_SUBSCRIPTIONS="List Subscriptions",
    SID_ADD_SUBSCRIPTION="Subscribe",
    SID_DEL_SUBSCRIPTION="Unsubscribe",
    SID_1ST_SUBSCRIPTION_PROMPT='Subscribing to a channel is a good idea',
    SID_SUBSCRIPTIONS_PROMPT='Here are your subscriptions:',
    SID_SUBSCRIPTION_ADD_PROMPT=(
        "You can subscribe to yet another channel. Enter the desired Channel ID "
        "or channel URL:"
    ),
    SID_SUB_ADDED="Subscription to channel $CHANNEL_NAME added",
    SID_SUB_EXISTS="You are already subscribed to channel $CHANNEL_NAME",
    SID_ENTER_CHANNEL_ID_PROMPT="Enter the desired Channel ID:",
    SID_NO_SUBS_PROMPT="You have no active subscriptions",
    SID_SELECT_SUB_ACTION_PROMPT='What do you want to do next?',
    SID_SUB_UNSUBSCRIBE_PROMPT='Are you sure?',
    SID_SUB_REMOVED="Done",
    SID_SUB_UNCHANGED="Subscription kept",
    SID_ANNC_GET_TITLE_PROMPT="Enter the announcement title:",
    SID_ANNC_GET_TEXT_PROMPT=(
        "Enter а description. This may be a short or a long text with links if need be"
    ),
    SID_ANNC_ROOT_PROMPT="Please choose a channel",
    SID_ANNC_CREATE_CHANNEL_PROMPT="Please create a channel first",
    SID_ANNC_NEW_CHANNEL="New Channel",
    SID_ANNC_SELECT_CHANNEL="Select Channel",
    SID_SELECT_THIS="Select",
    SID_VIEW_SUB_BTN="View",
    SID_DEL_SUB_BTN="Unsubscribe",
    SID_SHARE_SUB_BTN="Share Channel",
    SID_VIEW_CHANNEL_BTN="View",
    SID_EDIT_CHANNEL_BTN="Edit",
    SID_SHARE_CHANNEL_BTN="Sharing Options",
    SID_MORE="More",
    SID_NO_MORE_ANNCS='There is nothing else on this channel.',
    SID_SHOW_EARIER_ANNCS_PROMPT=('Do you want to see earlier announcements '
                                  'made on this channel?')
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
