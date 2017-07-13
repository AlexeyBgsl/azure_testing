from abc import ABC
from google.cloud import datastore
from bot.config import CONFIG


# See https://googlecloudplatform.github.io/google-cloud-python/stable/datastore-client.html

class BasicEntry(ABC):
    @classmethod
    def create(cls, table, data):
        return cls(table, table.update(data))

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

    def __init__(self, table):
        """Constructor"""
        self.table = table
        self.oid = None
        self.db_fields = []

    def to_dict(self):
        d = {}
        for key in self.db_fields:
            d[key] = getattr(self, key)
        return d

    def save(self):
        entity = self.table.update(self.to_dict(), self.oid)
        self.oid = entity.key.id

    def read(self):
        entity = self.table.read(self.oid)
        self.from_entity(entity)

    def delete(self):
        self.table.delete(self.oid)
        self.oid = None


class BasicTable(ABC):
    def __init__(self, kind, exclude_from_indexes=()):
        self.kind = kind
        self.client = datastore.Client(CONFIG['PROJECT_ID'])
        self.exclude_from_indexes = exclude_from_indexes

    def _get_key(self, oid=None):
        if oid:
            return self.client.key(self.kind, int(oid))
        return self.client.key(self.kind)

    def update(self, data, oid=None):
        entity = datastore.Entity(
            key=self._get_key(oid),
            exclude_from_indexes=self.exclude_from_indexes)
        entity.update(data)
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


class User(BasicEntry):
    def __init__(self, table, entity):
        super().__init__(table)
        self.add_db_field('fbid', 0)
        self.add_db_field('fbmsgseq', 0)
        if entity:
            self.from_entity(entity)


class Users(BasicTable):
    def __init__(self):
        super().__init__(kind="Users")

    def by_fbid(self, fbid):
        results = self.simple_query(fbid=fbid)
        if len(results) > 1:
            raise ValueError("FB ID must be unique")
        return User(self, entity=results[0]) if results else None


