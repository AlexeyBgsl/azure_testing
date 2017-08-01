"""
App Configuration
"""
import os

APP_ENV_GAE = (os.getenv('APP_ENV_GAE', '') == '1')
GCLOUD_PROJECT = os.getenv('GCLOUD_PROJECT', '')

if APP_ENV_GAE:
    # Production
    DEBUG = False
    TESTING = False
else:
    DEBUG = True
    TESTING = False
