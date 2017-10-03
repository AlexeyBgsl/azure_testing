import os


STORAGE_ACCOUNT_NAME = os.getenv('STORAGE_ACCOUNT_NAME', 'locanonetstorage')
assert STORAGE_ACCOUNT_NAME

STORAGE_ACCOUNT_KEY = os.getenv('STORAGE_ACCOUNT_KEY', 'lQHxQSZbERuw+T3zQYztS1qXt7dvgXTb+eXR58bFIpM2FqrMjZmB/9kTYzr7yNTjYWKAM5hnodjYdnHjUcZ1DQ==')
assert STORAGE_ACCOUNT_KEY

FB_PAGE_NAME = os.getenv('FB_PAGE_NAME', 'LocanoDbg-2074044709489393')
assert FB_PAGE_NAME

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://locanonet:HvoGyMSUgOsEHsLUNjmavx1eAqer7FJFFXAjnqvSeE2LbwMQOopp4HXd7UQP5ocPnkdUpT4gnjFRz6Kj4fZoCQ==@locanonet.documents.azure.com:10255/?ssl=true&replicaSet=globaldb')
assert MONGODB_URI

MONGODB_DB = os.getenv('MONGODB_DB', 'main')
assert MONGODB_DB
