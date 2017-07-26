from abc import ABC
from google.cloud import datastore
from bot.config import CONFIG


# See https://googlecloudplatform.github.io/google-cloud-python/stable/datastore-client.html

class BasicEntry(ABC):
    table = None

    def __add_db_property(self, name):
        if not name in self.db_fields:
            self.db_fields.append(name)

    def add_db_field(self, name, val = None):
        try:
            setattr(self, name, val)
        except AttributeError:
            pass
        self.__add_db_property(name)

    def from_entity(self, e):
        self.oid = e.key.id
        for key in e:
            if key != 'key':
                self.add_db_field(key, e[key])

    def __init__(self):
        assert self.table
        self.oid = None
        self.db_fields = []

    def to_dict(self):
        d = {}
        for key in self.db_fields:
            d[key] = getattr(self, key)
        return d

    def adjust_oid(self, entity):
        self.oid = entity.key.id

    def save(self):
        entity = self.table.update(self.to_dict(), self.oid)
        self.adjust_oid(entity)

    def read(self):
        entity = self.table.read(self.oid)
        self.from_entity(entity)

    def delete(self):
        self.table.delete(self.oid)
        self.oid = None


class BasicTable(ABC):
    client = datastore.Client(CONFIG['PROJECT_ID'])

    def __init__(self, kind, exclude_from_indexes=()):
        self.kind = kind
        self.exclude_from_indexes = exclude_from_indexes

    def _get_key(self, oid=None):
        if oid:
            return self.client.key(self.kind, int(oid))
        return self.client.key(self.kind)

    def entity(self, data, oid=None):
        entity = datastore.Entity(
            key=self._get_key(oid),
            exclude_from_indexes=self.exclude_from_indexes)
        entity.update(data)
        return entity

    def update(self, data, oid=None):
        entity = self.entity(data, oid)
        self.client.put(entity)
        return entity

    def read(self, oid):
        return self.client.get(self._get_key(oid))

    def delete(self, oid):
        self.client.delete(self._get_key(oid))

    def query(self):
        return self.client.query(kind=self.kind)

    def simple_query(self, **kwargs):
        query = self.query()
        for key in kwargs:
            query.add_filter(key, '=', kwargs[key])
        return list(query.fetch())


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

    def is_subscribed(self, chid):
        return chid in self.subscription

    def subscribe(self, chid, autosave=True):
        if chid not in self.subscriptions:
            self.subscriptions.append(chid)
            if autosave:
                self.save()

    def unsubscribe(self, chid, autosave=True):
        if chid in self.subscriptions:
            self.subscriptions.remove(chid)
            if autosave:
                self.save()


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

    def __init__(self, name=None, owner_uid=None, entity=None):
        super().__init__()
        self.add_db_field('owner_uid', owner_uid)
        self.add_db_field('name', name)
        self.add_db_field('desc', '')
        if entity:
            self.from_entity(entity)

    @property
    def chid(self):
        return self.oid

    @property
    def str_chid(self):
        s = str(self.oid).ljust(16, '0')
        return '{}-{}-{}-{}'.format(s[:4], s[4:8], s[8:12], s[12:16])
