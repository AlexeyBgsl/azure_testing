
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


class DataCenterResourceSet():
    def __init__(self):
        self.FileStorage = None
        self.Users = None
        self.Channels = None
        self.Anncs = None
        self.Strings = None

    def set(self, name, val):
        assert hasattr(self, name)
        setattr(self, name, val)


DCRS = DataCenterResourceSet()