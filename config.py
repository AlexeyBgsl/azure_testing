"""
App Configuration
"""
import os

CONFIG = dict(
    DEBUG=os.getenv('DEBUG', True),
    APP_LOG_FILE = os.getenv('APP_LOG_FILE', ''),
    TESTING = os.getenv('TESTING', False),
    LOGFMT='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    STORAGE_ACCOUNT_NAME = os.getenv('STORAGE_ACCOUNT_NAME', 'locanonetstorage'),
    STORAGE_ACCOUNT_KEY = os.getenv('STORAGE_ACCOUNT_KEY', 'lQHxQSZbERuw+T3zQYztS1qXt7dvgXTb+eXR58bFIpM2FqrMjZmB/9kTYzr7yNTjYWKAM5hnodjYdnHjUcZ1DQ=='),
    FB_PAGE_NAME = os.getenv('FB_PAGE_NAME', 'LocanoDbg-2074044709489393'),
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://locanonet:HvoGyMSUgOsEHsLUNjmavx1eAqer7FJFFXAjnqvSeE2LbwMQOopp4HXd7UQP5ocPnkdUpT4gnjFRz6Kj4fZoCQ==@locanonet.documents.azure.com:10255/?ssl=true&replicaSet=globaldb'),
    MONGODB_DB = os.getenv('MONGODB_DB', 'main'),
)
