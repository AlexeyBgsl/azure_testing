"""
Bot configuration
"""

import os

ACCESS_TOKEN_PRD = ('EAAUEkHk0iswBAIg6ZCMx7cAGysgWohTJq1rWN4GgAGm21Cnc72HHjrZB'
                    'jsIbLV8SoYwvux2j9ONAVyU9evSGzrQa03RZCigzsU47l2WfLqZBiP5w8'
                    '5Ak4ZAdYTMwVQmMnZBT8XQjVYuF0lk21JSiUwtP3PBNV5F3gTmtItzedh'
                    'cqFj4bnP5nR2')
ACCESS_TOKEN_DBG = ('EAATBF61P4qoBAOxtLJqx75i2e04c2CUCpfTCiOTaJCuZA81ZAVf33icr'
                    'xfElOXm50aBTlcTGtFnuyr5lZAPrV382eGCVZB58pb4AoSohRmyyV5qyw'
                    'XOsDBpM8HgE3ZCfN9rv7spE9ZCfqIDnj2tM9Tb5ZAm9fb3l296ZAJQgIn'
                    'QlO2ltaF4uAwqQ')

CHANNELS_INFO_URI = os.getenv('CHANNELS_BASE_URI',
                              'http://data.locano.net/channels/')
assert CHANNELS_INFO_URI


CONFIG = dict(
    ACCESS_TOKEN='',
    VERIFY_TOKEN='loc@no',
    PROJECT_ID='locano-172715',
    CHANNELS_INFO_URI=CHANNELS_INFO_URI,
    BOT_SENDER_GMAIL = os.getenv('BOT_SENDER_GMAIL',
                                 'locano.net@gmail.com'),
    BOT_SENDER_PASSWD = os.getenv('BOT_SENDER_PASSWD', '515716827'),
    FEEDBACK_DEST = os.getenv('FEEDBACK_DEST', 'botfeedback@locano.net'),
    FEEDBACK_SUBJ = os.getenv('FEEDBACK_SUBJ', 'Locano Bot Feedback'),
    FEEDBACK_BODY = os.getenv('FEEDBACK_BODY',
                              ('User: {first_name} {last_name}\n'
                               'FB ID: {fbid}\n'
                               'Text: {text}')),

    EXCEPTION_REPORT_DEST = os.getenv('EXCEPTION_REPORT_DEST',
                                      'botexception@locano.net'),
    EXCEPTION_REPORT_SUBJ = os.getenv('EXCEPTION_REPORT_SUBJ',
                                      'Locano Bot Exception'),
    EXCEPTION_REPORT_BODY = os.getenv('EXCEPTION_REPORT_BODY',
                                      ('FB ID: {fbid}\n'
                                       'Text: {text}'))
)

def init_config():
    if os.getenv('PRODUCTION_APP_ENV', '') == '1':
        CONFIG['ACCESS_TOKEN'] = ACCESS_TOKEN_PRD
    else:
        CONFIG['ACCESS_TOKEN'] = ACCESS_TOKEN_DBG


def is_correct_token(token):
    """ Validation tocken check """
    return token == CONFIG['VERIFY_TOKEN']
