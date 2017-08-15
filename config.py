"""
App Configuration
"""
import os

PRODUCTION_APP_ENV = (os.getenv('PRODUCTION_APP_ENV', '') == '1')
DEBUG = os.getenv('DEBUG', True)
APP_LOG_FILE = os.getenv('APP_LOG_FILE', '')

if PRODUCTION_APP_ENV:
    # Production
    TESTING = False
else:
    TESTING = False

LOGFMT='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
