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
CONFIG = dict(
    ACCESS_TOKEN='',
    VERIFY_TOKEN='loc@no',
    PROJECT_ID='locano-172715'
)


def init_config():
    if os.getenv('PRODUCTION_APP_ENV', '') == '1':
        CONFIG['ACCESS_TOKEN'] = ACCESS_TOKEN_PRD
    else:
        CONFIG['ACCESS_TOKEN'] = ACCESS_TOKEN_DBG


def is_correct_token(token):
    """ Validation tocken check """
    return token == CONFIG['VERIFY_TOKEN']
