import re
from db.datastore import BasicEntry, BasicTable, retry_db


class Users(BasicTable):
    def __init__(self):
        super().__init__(kind="Users")

    def by_fbid(self, fbid):
        results = self.simple_query(fbid=fbid)
        if len(results) > 1:
            raise ValueError("FB ID must be unique")
        return results[0] if results else None


class User(BasicEntry):
    table = Users()

    @classmethod
    def create(cls, data):
        return cls(cls.table.entity(data))

    @classmethod
    def by_fbid(cls, fbid):
        e = cls.table.by_fbid(fbid)
        return cls(e) if e else None

    def __init__(self, entity):
        super().__init__()
        self.add_db_field('fbid', 0)
        self.add_db_field('fbmsgseq', 0)
        self.add_db_field('subscriptions', [])
        if entity:
            self.from_entity(entity)

    def subscribe(self, chid):
        return subscribe(uid=self.oid, chid=chid)

    def unsubscribe(self, chid):
        return unsubscribe(uid=self.oid, chid=chid)

    def _subscribe(self, chid):
        if chid not in self.subscriptions:
            self.subscriptions.append(chid)
            return True
        return False

    def _unsubscribe(self, chid):
        if chid in self.subscriptions:
            self.subscriptions.remove(chid)
            return True
        return False

    def delete(self):
        while len(self.subscriptions):
            unsubscribe(self.oid, self.subscriptions[0])
        super().delete()


class Channels(BasicTable):
    def __init__(self):
        super().__init__(kind="Channels", exclude_from_indexes=('desc',))


class Channel(BasicEntry):
    table = Channels()

    @classmethod
    def by_owner_uid(cls, owner_uid):
        return cls.table.simple_query(owner_uid=owner_uid)

    @classmethod
    def by_chid(cls, chid):
        e = cls.table.read(chid)
        if e:
            return cls(entity=e) if e else None

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
        super().__init__()
        self.add_db_field('owner_uid', owner_uid)
        self.add_db_field('name', name)
        self.add_db_field('desc', '')
        self.add_db_field('subscribers', [])
        if entity:
            self.from_entity(entity)

    def delete(self):
        while len(self.subscribers):
            unsubscribe(uid=self.subscribers[0], chid=self.chid)
        super().delete()

    @property
    def chid(self):
        return self.oid

    @property
    def str_chid(self):
        s = str(self.oid).ljust(16, '0')
        return '{}-{}-{}-{}'.format(s[:4], s[4:8], s[8:12], s[12:16])

    def subscribe(self, uid):
        return subscribe(uid=uid, chid=self.oid)

    def unsubscribe(self, uid):
        return unsubscribe(uid=uid, chid=self.oid)

    def _subscribe(self, uid):
        if uid not in self.subscribers:
            self.subscribers.append(uid)
            return True
        return False

    def _unsubscribe(self, uid):
        if uid in self.subscribers:
            self.subscribers.remove(uid)
            return True
        return False


@retry_db
def subscribe(uid, chid):
    with BasicTable.client.transaction() as t:
        ue = User.entity_by_oid(uid)
        ce = Channel.entity_by_oid(chid)
        if ue and ce:
            u = User(entity=ue)
            c = Channel(entity=ce)
            if u._subscribe(chid):
                t.put(u.to_entity())
            if c._subscribe(uid):
                t.put(c.to_entity())
            return True
    return False


@retry_db
def unsubscribe(uid, chid):
    with BasicTable.client.transaction() as t:
        ue = User.entity_by_oid(uid)
        if ue:
            u = User(entity=ue)
            if u._unsubscribe(chid):
                t.put(u.to_entity())
        ce = Channel.entity_by_oid(chid)
        if ce:
            c = Channel(entity=ce)
            if c._unsubscribe(uid):
                t.put(c.to_entity())


class Anncs(BasicTable):
    def __init__(self):
        super().__init__(kind="Announcements",
                         exclude_from_indexes=('desc', 'title', ))


class Annc(BasicEntry):
    table = Anncs()

    @classmethod
    def by_owner_uid(cls, owner_uid):
        return cls.table.simple_query(owner_uid=owner_uid)

    @classmethod
    def by_chid(self, chid):
        return self.table.simple_query(chid=chid)

    def __init__(self, title=None, chid=None, owner_uid=None, entity=None):
        super().__init__()
        self.add_db_field('title', title)
        self.add_db_field('chid', chid)
        self.add_db_field('owner_uid', owner_uid)
        self.add_db_field('desc', '')
        if entity:
            self.from_entity(entity)


class Strings(BasicTable):
    def __init__(self):
        super().__init__(kind="Strings")

    def by_sid(self, sid):
        results = self.simple_query(sid=sid)
        if len(results) > 1:
            raise ValueError("String ID must be unique")
        return results[0] if len(results) else None


class String(BasicEntry):
    table = Strings()
    LOCALE_MARKER = 'locale'
    LOCALE_DELIMITER = '.'
    DEFAULT_LOCALE = 'en_US'

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
        results = String.table.simple_query()
        for e in results:
            s = String()
            s.from_entity(e)
            l.append(s)
        return l

    def __init__(self, sid=None):
        super().__init__()
        self.add_db_field('sid', '')
        if sid:
            self.load(sid)

    @property
    def in_db(self):
        return self.oid is not None

    def load(self, sid):
        e = self.table.by_sid(sid)
        if e:
            self.from_entity(e)
            return True
        self.sid = sid
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
        super().__init__(kind="Handlers")

    def by_fbid(self, fbid):
        results = self.simple_query(fbid=fbid)
        if len(results) > 1:
            raise ValueError("FB ID must be unique")
        return results[0] if results else None


class MsgHandler(BasicEntry):
    table = MsgHandlers()

    @classmethod
    def get_by_fbid(cls, fbid, auto_remove=True):
        e = cls.table.by_fbid(fbid)
        if e:
            if auto_remove:
                cls.table.delete(e.key.id)
            return cls(entity=e)
        return None

    @classmethod
    def create_or_update(cls, fbid, payload, auto_save=True):
        e = cls.table.by_fbid(fbid)
        h = cls(entity=e)
        h.set(fbid=fbid, payload=payload)
        if auto_save:
            h.save()
        return h

    def __init__(self, entity=None):
        super().__init__()
        if entity:
            self.from_entity(entity)

    def set(self, fbid, payload):
        self.add_db_field('fbid', fbid)
        self.add_db_field('payload', payload)

