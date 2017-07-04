"""
App Configuration
"""
import os

if os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine/'):
    # Production
    DEBUG = False
    TESTING = False
else:
    DEBUG = True
    TESTING = False
