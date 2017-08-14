"""
App Configuration
"""
import os

PRODUCTION_APP_ENV = (os.getenv('PRODUCTION_APP_ENV', '') == '1')
DEBUG = os.getenv('DEBUG', True)

if PRODUCTION_APP_ENV:
    # Production
    TESTING = False
else:
    TESTING = False
