from abc import ABC
from google.cloud import datastore
from bot.config import CONFIG

# See https://googlecloudplatform.github.io/google-cloud-python/stable/datastore-client.html

class BasicEntry(ABC):
    @classmethod
    def create(cls, table, data):
        return cls(table, table.create(data))

    @property
    def id(self):
        return self.entity.key.id

    def __init__(self, table, entity):
        self.table = table
        self.entity = entity

    def update(self, **kwargs):
        if kwargs is not None:
            for key in kwargs:
                self.entity[key] = kwargs[key]
        self.table.update(self.entity, self.id)

    def read(self):
        self.table.read(self.id)

    def delete(self):
        self.table.delete(self.id)


class BasicTable(ABC):
    def __init__(self, kind, exclude_from_indexes=()):
        self.kind = kind
        self.client = datastore.Client(CONFIG['PROJECT_ID'])
        self.exclude_from_indexes = exclude_from_indexes

    def _get_key(self, oid=None):
        if oid:
            return self.client.key(self.kind, int(oid))
        return self.client.key(self.kind)

    def _update(self, data, oid):
        entity = datastore.Entity(
            key=self._get_key(oid),
            exclude_from_indexes=self.exclude_from_indexes)
        entity.update(data)
        self.client.put(entity)
        return entity

    def update(self, data, oid):
        return self._update(data, oid)

    def create(self, data):
        return self.update(data, None)

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
    pass


class Users(BasicTable):
    def __init__(self):
        super().__init__(kind="Users")

    def by_fbid(self, fbid):
        results = self.simple_query(fbid=fbid)
        if len(results) > 1:
            raise ValueError("FB ID must be unique")
        return User(self, results[0]) if results else None
