from abc import ABC
import logging
import functools
from google.cloud import datastore, exceptions
from db.config import GCLOUD_PROJECT


MAX_RETRY_ATTEMPTS=5


def retry_db(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        last_exception = None
        for i in range(MAX_RETRY_ATTEMPTS):
            try:
                return f(*args, **kwargs)
            except exceptions.Conflict as e:
                logging.warning("Retry#%d: function %s due to %s",
                                i, f.__name__, str(e))
                last_exception = e
                continue
        raise last_exception

    return wrapped


# See https://googlecloudplatform.github.io/google-cloud-python/stable/datastore-client.html

class BasicEntry(ABC):
    table = None

    @classmethod
    def entity_by_oid(cls, oid):
        return cls.table.read(oid)

    @classmethod
    def by_oid(cls, oid):
        e = cls.entity_by_oid(oid)
        return cls(entity = e) if e else None

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

    def __init__(self, entity=None):
        assert self.table
        self.oid = None
        self.db_fields = []
        if entity:
            self.from_entity(entity)

    def to_dict(self):
        d = {}
        for key in self.db_fields:
            d[key] = getattr(self, key)
        return d

    def to_entity(self):
        return self.table.entity(self.to_dict(), self.oid)

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
    client = datastore.Client(GCLOUD_PROJECT)

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

    @retry_db
    def update(self, data, oid=None):
        entity = self.entity(data, oid)
        self.client.put(entity)
        return entity

    def read(self, oid):
        return self.client.get(self._get_key(oid))

    @retry_db
    def delete(self, oid):
        self.client.delete(self._get_key(oid))

    def query(self):
        return self.client.query(kind=self.kind)

    def simple_query(self, **kwargs):
        query = self.query()
        for key in kwargs:
            query.add_filter(key, '=', kwargs[key])
        return list(query.fetch())
