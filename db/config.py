
VNAMES=['STORAGE_ACCOUNT_NAME',
        'STORAGE_ACCOUNT_KEY',
        'FB_PAGE_NAME',
        'MONGODB_URI',
        'MONGODB_DB']

CONFIG = dict()


def store_config(values):
    global CONFIG
    for vname in VNAMES:
        if vname not in values:
            raise ValueError('Mandatory config absent: {}'.format(vname))
        CONFIG[vname] = values[vname]


class DCRS(): # Data Center Resource Set
    @classmethod
    def set(cls, name, val):
        setattr(cls, name, val)
