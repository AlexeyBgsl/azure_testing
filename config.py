import os


STORAGE_ACCOUNT_NAME = os.getenv('STORAGE_ACCOUNT_NAME', 'locanobot')
assert STORAGE_ACCOUNT_NAME

STORAGE_ACCOUNT_KEY = os.getenv('STORAGE_ACCOUNT_KEY', 'aJfouPGJhubsGpJsprx7C2P/wXvMNjrBLZSKySJd+DdymOUZ6IKldraDHS/32pLJpmhdn38ee7MqcN67nlLiFA==')
assert STORAGE_ACCOUNT_KEY

FB_PAGE_NAME = os.getenv('FB_PAGE_NAME', 'LocanoDbg-2074044709489393')
assert FB_PAGE_NAME

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://locanonet:HvoGyMSUgOsEHsLUNjmavx1eAqer7FJFFXAjnqvSeE2LbwMQOopp4HXd7UQP5ocPnkdUpT4gnjFRz6Kj4fZoCQ==@locanonet.documents.azure.com:10255/?ssl=true&replicaSet=globaldb')
assert MONGODB_URI

MONGODB_DB = os.getenv('MONGODB_DB', 'main')
assert MONGODB_DB
