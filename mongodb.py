from abc import ABC
import logging
from pymongo import MongoClient
from bson.objectid import ObjectId
from db.config import MONGODB_URI, MONGODB_DB


OID_KEY=u'_id'


class EntryField(object):
    def __init__(self, name, val):
        self.name = name
        self.val = val


class UpdateOps(object):
    def __init__(self, op=None, val=None):
        self.opts = {}
        if op:
            self.add(op, val)

    def add(self, op, val):
        assert op and val and isinstance(val, dict)
        if not self.opts.get(op):
            self.opts[op] = {}
        self.opts[op].update(val)

    @property
    def update(self):
        return self.opts


class BasicEntry(ABC):
    table = None
    INIT_FIELDS = None

    @classmethod
    def by_oid(cls, oid):
        e = cls.table.read(oid)
        return cls(entity = e) if e else None

    def __add_db_property(self, name):
        if not name in self.db_fields:
            self.db_fields.append(name)

    def from_entity(self, e):
        self.adjust_oid(e)
        self.from_dict(e)

    def add_db_field(self, name, val = None):
        try:
            setattr(self, name, val)
        except AttributeError:
            pass
        self.__add_db_property(name)

    def __init__(self, **kwargs):
        assert self.table
        assert self.INIT_FIELDS
        self.oid = None
        self.db_fields = []
        for f in self.INIT_FIELDS:
            assert f.name != 'entity'
            val = kwargs[f.name] if f.name in kwargs else f.val
            self.add_db_field(f.name, val)
        if 'entity' in kwargs and kwargs['entity']:
            self.from_entity(kwargs['entity'])

    def to_dict(self):
        d = {}
        for key in self.db_fields:
            d[key] = getattr(self, key)
        return d

    def from_dict(self, d):
        for key in d:
            if key != OID_KEY:
                self.add_db_field(key, d[key])

    def adjust_oid(self, entity):
        self.oid = entity[OID_KEY]

    def save(self):
        if self.oid:
            self.update(op='$set', val=self.to_dict())
        else:
            result = self.table.collection.insert_one(self.to_dict())
            self.oid = result.inserted_id

    def update_ex(self, ops):
        assert self.oid
        return self.table.collection.update_one({OID_KEY: self.oid}, ops.update)

    def update(self, op, val):
        assert self.oid
        return self.update_ex(UpdateOps(op=op, val=val))

    def read(self):
        entity = self.table.read(self.oid)
        self.from_entity(entity)

    def delete(self):
        self.table.delete(self.oid)
        self.oid = None


class BasicTable(ABC):
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB]

    def __init__(self, col_name):
        self.collection = self.db[col_name]

    def read(self, oid):
        assert oid
        return self.collection.find_one({OID_KEY: oid})

    def delete(self, oid):
        self.collection.find_one_and_delete({OID_KEY: oid})

    def query(self, **kwargs):
        return list(self.collection.find(kwargs))

    def query_unique(self, **kwargs):
        results = self.collection.find(kwargs)
        if results.count() > 1:
            raise ValueError("%s must be unique", **kwargs)
        for r in results.limit(-1):
            return r
        return None
