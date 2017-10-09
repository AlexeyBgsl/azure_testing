import re
import logging
import uuid
import tempfile
import os
import pyqrcode
import datetime
from .mongodb import BasicEntry, BasicTable, EntryField, UpdateOps
from .config import CONFIG, DCRS

MAX_CHID_CYPHERS = 9


def m_link(ref):
    return 'http://m.me/' + CONFIG['FB_PAGE_NAME'] + '?ref=' + ref

def _blob_fname(fname):
    return CONFIG['FB_PAGE_NAME'] + '.' + fname


class User(BasicEntry):
    INIT_FIELDS = [
        EntryField('fbid', 0),
        EntryField('fbmsgseq', 0),
        EntryField('state_payload', '')
    ]

    def __init__(self, table, entity=None):
        super().__init__(table=table, entity=entity)

    def delete(self):
        channels = Channel.table.all_subscribed(self.oid)
        for c in channels:
            c.unsubscribe(self.oid)
        super().delete()


class Users(BasicTable):
    obj_type = User

    def __init__(self, mongodb_uri, db_name, fb_page_name):
        super().__init__(mongodb_uri=mongodb_uri,
                         db_name=db_name,
                         fb_page_name=fb_page_name,
                         col_name="Users")

    def by_fbid(self, fbid):
        return self.find_unique(fbid=fbid)

    def create(self, fbid, fb_profile):
        obj = self.obj_type(table=self)
        obj.from_dict(fb_profile)
        obj.fbid = fbid
        obj.save_unique(fbid=fbid)


class Channel(BasicEntry):
    INIT_FIELDS = [
        EntryField('owner_uid', None),
        EntryField('name', None),
        EntryField('uchid', ''),
        EntryField('status', 'pending'),
        EntryField('desc', ''),
        EntryField('subs', []),
        EntryField('messenger_code', ''),
        EntryField('qr_code', ''),
        EntryField('pic_url', ''),
    ]

    def _alloc_uchid(self):
        while True:
            self.uchid = self.table.gen_uchid()
            self.status = 'pending'
            super().save()
            r = self.table._find(uchid=self.uchid)
            assert len(r)
            if len(r) == 1:
                self.update(op=UpdateOps.Supported.SET, status='ready')
                break
            logging.info("User CHID#%s is already in use. Regenerating... ",
                         self.uchid)

    def __init__(self, table, entity=None):
        super().__init__(table=table, entity=entity)

    def set_code(self, ref=None, messenger_code_url=None):
        assert self.oid
        opts = UpdateOps()
        blob_fname = _blob_fname(self.uchid)
        if ref:
            url = pyqrcode.create(m_link(ref), error='Q')
            png_fname = os.path.join(tempfile.gettempdir(), self.uchid)
            url.png(png_fname, scale=5)
            DCRS.FileStorage.upload(png_fname, 'qr-code', blob_fname,
                                    content_type='image/png')
            os.remove(png_fname)
            url = DCRS.FileStorage.get_url('qr-code', blob_fname)
            opts.add(UpdateOps.Supported.SET, qr_code=url)
        if messenger_code_url:
            DCRS.FileStorage.upload_from_url(messenger_code_url,
                                         'messenger-code',
                                         blob_fname)
            url = DCRS.FileStorage.get_url('messenger-code', blob_fname)
            opts.add(UpdateOps.Supported.SET, messenger_code=url)
        if opts.has_update:
            self.update_ex(opts)

    def set_cover_pic(self, url):
        self.update(UpdateOps.Supported.SET, pic_url=url)

    @property
    def cover_pic(self):
        return self.pic_url if self.pic_url else self.qr_code

    def save(self):
        if not self.oid:
            self._alloc_uchid()
        else:
            super().save()

    @property
    def str_uchid(self):
        return '{}-{}-{}'.format(self.uchid[:3], self.uchid[3:6], self.uchid[6:9])

    def subscribe(self, uid):
        r = self.update(op=UpdateOps.Supported.ADD_TO_LIST, subs=uid)
        if not r:
            logging.warning("U#%s: cannot subscribe user %s",
                            str(self.oid), str(uid))

    def unsubscribe(self, uid):
        r = self.update(op=UpdateOps.Supported.DEL_FROM_LIST, subs=uid)
        if not r:
            logging.warning("U#%s: cannot unsubscribe user %s",
                            str(self.oid), str(uid))

    def delete(self):
        DCRS.FileStorage.remove('qr-code', self.uchid)
        DCRS.FileStorage.remove('messenger-code', self.uchid)
        super().delete()


class Channels(BasicTable):
    obj_type = Channel

    @staticmethod
    def gen_uchid():
        uchid = uuid.uuid4().int % pow(10, MAX_CHID_CYPHERS)
        return str(uchid).ljust(MAX_CHID_CYPHERS, '0')

    @staticmethod
    def uchid_from_str(str):
        uchid = re.sub(r"\s+", "", str, flags=re.UNICODE)
        uchid = re.sub(r"-", "", uchid)
        return uchid if uchid.isnumeric() else None

    def __init__(self, mongodb_uri, db_name, fb_page_name):
        super().__init__(mongodb_uri=mongodb_uri,
                         db_name=db_name,
                         fb_page_name=fb_page_name,
                         col_name="Channels")

    def _find(self, **kwargs):
        return super().find(**kwargs)

    def find(self, **kwargs):
        return super().find(status='ready', **kwargs)


    def find_unique(self, **kwargs):
        return super().find_unique(status='ready', **kwargs)

    def all_subscribed(self, uid):
        return self.find(subs=uid)

    def by_uchid_str(self, str):
        uchid = self.uchid_from_str(str)
        return self.find_unique(uchid=uchid) if uchid else None

    def new(self, name, owner_uid):
        c = super().new()
        c.name = name
        c.owner_uid = owner_uid
        c._alloc_uchid()
        return c


class Annc(BasicEntry):
    INIT_FIELDS = [
        EntryField('title', None),
        EntryField('chid', None),
        EntryField('owner_uid', None),
        EntryField('text', ''),
        EntryField('created', '')
    ]

    def __init__(self, table, title=None, chid=None, owner_uid=None,
                 entity=None):
        super().__init__(table=table, title=title, chid=chid,
                         owner_uid=owner_uid, entity=entity)
        if not entity:
            self.created = datetime.datetime.utcnow()


class Anncs(BasicTable):
    obj_type = Annc

    def __init__(self, mongodb_uri, db_name, fb_page_name):
        super().__init__(mongodb_uri=mongodb_uri,
                         db_name=db_name,
                         fb_page_name=fb_page_name,
                         col_name="Anncs")


class String(BasicEntry):
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

    def __init__(self, table, sid=None, entity=None):
        super().__init__(table=table, sid=sid, entity=entity)
        if sid:
            e = self.table.raw_find_unique(sid=sid)
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


class Strings(BasicTable):
    obj_type = String

    def __init__(self, mongodb_uri, db_name, fb_page_name):
        super().__init__(mongodb_uri=mongodb_uri,
                         db_name=db_name,
                         fb_page_name=fb_page_name,
                         col_name="Strings")


def update_defaults_models():
    collection_types = [ Users, Channels, Anncs, Strings ]
    for t in collection_types:
        DCRS.set(t.__name__, t(mongodb_uri=CONFIG['MONGODB_URI'],
                               db_name=CONFIG['MONGODB_DB'],
                               fb_page_name=CONFIG['FB_PAGE_NAME']))
