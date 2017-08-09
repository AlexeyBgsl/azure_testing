import re
import logging
import uuid
from .mongodb import BasicEntry, BasicTable, EntryField, UpdateOps

MAX_CHID_CYPHERS = 9


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

    @classmethod
    def by_fbid(cls, fbid):
        e = cls.table.by_fbid(fbid)
        return cls(entity=e) if e else None

    def delete(self):
        channels = self.table.all_subscribed(self.oid)
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
        EntryField('chid', ''),
        EntryField('status', 'pending'),
        EntryField('desc', ''),
        EntryField('subs', [])
    ]

    @staticmethod
    def get_chid():
        chid = uuid.uuid4().int % pow(10, MAX_CHID_CYPHERS)
        return str(chid).ljust(MAX_CHID_CYPHERS, '0')

    @classmethod
    def by_owner_uid(cls, owner_uid):
        return cls.table.query(owner_uid=owner_uid, status='ready')

    @classmethod
    def by_chid(cls, chid):
        e = cls.table.query_unique(chid=chid, status='ready')
        if e:
            return cls(entity=e) if e else None

    @classmethod
    def all_subscribed(cls, uid):
        return [cls(entity=e) for e in cls.table.query(subs=uid,
                                                       status='ready')]

    @staticmethod
    def chid_from_str(str):
        chid = re.sub(r"\s+", "", str, flags=re.UNICODE)
        chid = re.sub(r"-", "", chid)
        return chid if chid.isnumeric() else None

    @classmethod
    def by_chid_str(cls, str):
        chid = cls.chid_from_str(str)
        return cls.by_chid(chid) if chid else None

    def __init__(self, name=None, owner_uid=None, entity=None):
        super().__init__(name=name, owner_uid=owner_uid, entity=entity)

    def save(self):
        if not self.oid:
            while True:
                self.chid = self.get_chid()
                self.status = 'pending'
                super().save()
                r = self.table.query(chid=self.chid)
                if len(r) == 1:
                    self.status = 'ready'
                    self.update_db(op=UpdateOps.Supported.SET,
                                   val={'status': 'ready'})
                    break
        else:
            super().save()

    @property
    def str_chid(self):
        return '{}-{}-{}'.format(self.chid[:3], self.chid[3:6], self.chid[6:9])

    def subscribe(self, uid):
        r = self.update(op=UpdateOps.Supported.ADD_TO_LIST, val={"subs": uid})
        if r.matched_count == 1:
            if uid not in self.subs:
                self.subs.append(uid)
        else:
            logging.warning("U#%s: cannot subscribe user %s",
                            str(self.oid), str(uid))

    def unsubscribe(self, uid):
        r = self.update(op=UpdateOps.Supported.DEL_FROM_LIST,
                        val={"subs": uid})
        if r.matched_count == 1:
            if uid in self.subs:
                self.subs.remove(uid)
        else:
            logging.warning("U#%s: cannot unsubscribe user %s",
                            str(self.oid), str(uid))


class Anncs(BasicTable):
    def __init__(self):
        super().__init__(col_name="Channels")


class Annc(BasicEntry):
    table = Anncs()
    INIT_FIELDS = [
        EntryField('title', None),
        EntryField('chid', None),
        EntryField('owner_uid', None),
        EntryField('desc', '')
    ]

    @classmethod
    def by_owner_uid(cls, owner_uid):
        return cls.table.query(owner_uid=owner_uid)

    @classmethod
    def by_chid(self, chid):
        return self.table.query(chid=chid)

    def __init__(self, title=None, chid=None, owner_uid=None, entity=None):
        super().__init__(title=title, chid=chid, owner_uid=owner_uid,
                         entity=entity)


class Strings(BasicTable):
    def __init__(self):
        super().__init__(col_name="Strings")

    def by_sid(self, sid):
        return self.query_unique(sid=sid)


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

    @classmethod
    def all(cls):
        l = []
        results = String.table.query()
        for e in results:
            s = String()
            s.from_entity(e)
            l.append(s)
        return l

    def __init__(self, sid=None):
        super().__init__(sid=sid)
        if sid:
            e = self.table.by_sid(sid)
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

    def by_fbid(self, fbid):
        return self.query_unique(fbid=fbid)


class MsgHandler(BasicEntry):
    table = MsgHandlers()
    INIT_FIELDS = [
        EntryField('fbid', None),
        EntryField('payload', None)
    ]

    @classmethod
    def get_by_fbid(cls, fbid, auto_remove=True):
        e = cls.table.by_fbid(fbid)
        if e:
            h = cls(entity=e)
            if auto_remove:
                h.delete()
            return h
        return None

    @classmethod
    def create_or_update(cls, fbid, payload, auto_save=True):
        e = cls.table.by_fbid(fbid)
        h = cls(entity=e)
        h.set(fbid=fbid, payload=payload)
        if auto_save:
            h.save()
        return h

    def set(self, fbid, payload):
        self.fbid = fbid
        self.payload = payload

