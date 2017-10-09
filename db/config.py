
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


class DataCenterResource:
    def attach(self, dcrc):
        assert dcrc
        self.dcrc = dcrc
        assert hasattr(dcrc, type(self).__name__)
        setattr(dcrc, type(self).__name__, self)


class DataCenterResourceSet():
    def __init__(self):
        self.FileStorage = None
        self.Users = None
        self.Channels = None
        self.Anncs = None
        self.Strings = None


DCRS = DataCenterResourceSet()