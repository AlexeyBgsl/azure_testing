"""
App Configuration
"""
import os

PRODUCTION_APP_ENV = (os.getenv('PRODUCTION_APP_ENV', '') == '1')


if PRODUCTION_APP_ENV:
    # Production
    DEBUG = False
    TESTING = False
else:
    DEBUG = True
    TESTING = False
