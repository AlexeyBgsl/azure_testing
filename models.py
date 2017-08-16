import re
import logging
import uuid
import tempfile
import os
import pyqrcode
from .mongodb import BasicEntry, BasicTable, EntryField, UpdateOps
from .blob import FileStorage
from .config import FB_PAGE_NAME

MAX_CHID_CYPHERS = 9


def _m_link(ref):
    return 'http://m.me/' + FB_PAGE_NAME + '?ref=' + ref

def _blob_fname(fname):
    return FB_PAGE_NAME + '.' + fname

class Users(BasicTable):
    def __init__(self):
        super().__init__(col_name="Users")

    def by_fbid(self, fbid):
        return self.query_unique(fbid=fbid)

class User(BasicEntry):
    table = Users()
    INIT_FIELDS = [
        EntryField('fbid', 0),
        EntryField('fbmsgseq', 0)
    ]

    @classmethod
    def create(cls, data):
        u = cls()
        u.from_dict(data)
        return u

    def delete(self):
        channels = Channel.table.all_subscribed(self.oid)
        for c in channels:
            c.unsubscribe(self.oid)
        super().delete()


class Channels(BasicTable):
    def __init__(self):
        super().__init__(col_name="Channels")


class Channel(BasicEntry):
    table = Channels()
    INIT_FIELDS = [
        EntryField('owner_uid', None),
        EntryField('name', None),
        EntryField('uchid', ''),
        EntryField('status', 'pending'),
        EntryField('desc', ''),
        EntryField('subs', []),
        EntryField('messenger_code', ''),
        EntryField('qr_code', ''),
    ]

    def _alloc_uchid(self):
        while True:
            self.uchid = self.gen_uchid()
            self.status = 'pending'
            super().save()
            r = super().find(uchid=self.uchid)
            assert len(r)
            if len(r) == 1:
                self.status = 'ready'
                self.update_db(op=UpdateOps.Supported.SET,
                               val={'status': 'ready'})
                break
            logging.info("User CHID#%s is already in use. Regenerating... ",
                         self.uchid)

    @staticmethod
    def gen_uchid():
        uchid = uuid.uuid4().int % pow(10, MAX_CHID_CYPHERS)
        return str(uchid).ljust(MAX_CHID_CYPHERS, '0')

    @classmethod
    def find(cls, **kwargs):
        return super().find(status='ready', **kwargs)

    @classmethod
    def find_unique(cls, **kwargs):
        return super().find_unique(status='ready', **kwargs)

    @classmethod
    def all_subscribed(cls, uid):
        return cls.find(subs=uid)

    @staticmethod
    def uchid_from_str(str):
        uchid = re.sub(r"\s+", "", str, flags=re.UNICODE)
        uchid = re.sub(r"-", "", uchid)
        return uchid if uchid.isnumeric() else None

    @classmethod
    def by_uchid_str(cls, str):
        uchid = cls.uchid_from_str(str)
        return cls.find_unique(uchid=uchid) if uchid else None

    @classmethod
    def create(cls, name, owner_uid):
        c = cls()
        c.name = name
        c.owner_uid = owner_uid
        c._alloc_uchid()
        return c

    def __init__(self, entity=None):
        super().__init__(entity=entity)

    def set_code(self, ref=None, messenger_code_url=None):
        assert self.oid
        opts = UpdateOps()
        blob_fname = _blob_fname(self.uchid)
        if ref:
            url = pyqrcode.create(_m_link(ref), error='Q')
            png_fname = os.path.join(tempfile.gettempdir(), self.uchid)
            url.png(png_fname, scale=5)
            FileStorage.upload(png_fname, 'qr-code', blob_fname,
                               content_type='image/png')
            os.remove(png_fname)
            self.qr_code = FileStorage.get_url('qr-code', blob_fname)
            opts.add(UpdateOps.Supported.SET, val={'qr_code': self.qr_code})
        if messenger_code_url:
            FileStorage.upload_from_url(messenger_code_url,
                                        'messenger-code',
                                        blob_fname)
            self.messenger_code = FileStorage.get_url('messenger-code',
                                                      blob_fname)
            opts.add(UpdateOps.Supported.SET,
                     val={'messenger_code': self.messenger_code})
        if opts.has_update:
            self.update_db_ex(opts)

    def save(self):
        if not self.oid:
            self._alloc_uchid()
        else:
            super().save()

    @property
    def str_uchid(self):
        return '{}-{}-{}'.format(self.uchid[:3], self.uchid[3:6], self.uchid[6:9])

    def subscribe(self, uid):
        r = self.update_db(op=UpdateOps.Supported.ADD_TO_LIST, val={"subs": uid})
        if r.matched_count == 1:
            if uid not in self.subs:
                self.subs.append(uid)
        else:
            logging.warning("U#%s: cannot subscribe user %s",
                            str(self.oid), str(uid))

    def unsubscribe(self, uid):
        r = self.update_db(op=UpdateOps.Supported.DEL_FROM_LIST,
                           val={"subs": uid})
        if r.matched_count == 1:
            if uid in self.subs:
                self.subs.remove(uid)
        else:
            logging.warning("U#%s: cannot unsubscribe user %s",
                            str(self.oid), str(uid))

    def delete(self):
        FileStorage.remove('qr-code', self.uchid)
        FileStorage.remove('messenger-code', self.uchid)
        super().delete()


class Anncs(BasicTable):
    def __init__(self):
        super().__init__(col_name="Anncs")


class Annc(BasicEntry):
    table = Anncs()
    INIT_FIELDS = [
        EntryField('title', None),
        EntryField('chid', None),
        EntryField('owner_uid', None),
        EntryField('desc', '')
    ]

    def __init__(self, title=None, chid=None, owner_uid=None, entity=None):
        super().__init__(title=title, chid=chid, owner_uid=owner_uid,
                         entity=entity)


class Strings(BasicTable):
    def __init__(self):
        super().__init__(col_name="Strings")


class String(BasicEntry):
    table = Strings()
    LOCALE_MARKER = 'locale'
    LOCALE_DELIMITER = ':'
    DEFAULT_LOCALE = 'en_US'
    INIT_FIELDS = [
        EntryField('sid', '')
    ]

    @classmethod
    def locale_aname(cls, locale):
        return cls.LOCALE_MARKER + cls.LOCALE_DELIMITER + locale

    @classmethod
    def locale_by_aname(cls, aname):
        t = aname.split(cls.LOCALE_DELIMITER)
        if len(t) == 2 and t[0] == cls.LOCALE_MARKER:
            return t[1]
        return None

    def __init__(self, sid=None):
        super().__init__(sid=sid)
        if sid:
            e = self.table.query_unique(sid=sid)
            if e:
                self.from_entity(e)

    @property
    def in_db(self):
        if self.oid:
            e = self.table.by_sid(self.oid)
            return e is not None
        return False

    def set(self, locale, text):
        self.add_db_field(self.locale_aname(locale), text)

    def get(self, locale):
        try:
            return getattr(self, self.locale_aname(locale))
        except AttributeError:
            return None

    def list(self):
        l = []
        for key in self.db_fields:
            locale = self.locale_by_aname(key)
            if locale:
                l.append(locale)
        return l


class MsgHandlers(BasicTable):
    def __init__(self):
        super().__init__(col_name="Handlers")


class MsgHandler(BasicEntry):
    table = MsgHandlers()
    INIT_FIELDS = [
        EntryField('fbid', None),
        EntryField('payload', None)
    ]
