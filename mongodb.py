from abc import ABC
from enum import Enum
from pymongo import MongoClient
from bson.objectid import ObjectId
from .config import MONGODB_URI, MONGODB_DB


OID_KEY=u'_id'


def _adjust_mongodb_db_name(s):
    # https://docs.mongodb.com/manual/reference/limits/#naming-restrictions
    for c in '/\. "$*<>:|?':
        s = s.replace(c, '-')
    return s


class EntryField(object):
    def __init__(self, name, val):
        self.name = name
        self.val = val


class UpdateOps(object):
    class Supported(Enum):
        SET = '$set'
        ADD_TO_LIST = '$addToSet'
        DEL_FROM_LIST = '$pull'

    def __init__(self, op=None, **kwargs):
        self.has_update = False
        self.opts = {}
        if op and kwargs:
            self.add(op, **kwargs)

    def add(self, op, **kwargs):
        assert op
        assert isinstance(op, self.Supported)
        assert kwargs
        _op = op.value
        if not self.opts.get(_op):
            self.opts[_op] = {}
        self.opts[_op].update(kwargs)
        self.has_update = True

    @property
    def update(self):
        return self.opts


class BasicEntry(ABC):
    table = None
    INIT_FIELDS = None

    @classmethod
    def by_oid(cls, oid):
        if isinstance(oid, str):
            oid = ObjectId(oid)
        e = cls.table.read(oid)
        return cls(entity = e) if e else None

    @classmethod
    def all(cls):
        return cls.find()

    @classmethod
    def find(cls, **kwargs):
        return [cls(entity=e) for e in cls.table.query(**kwargs)]

    @classmethod
    def find_unique(cls, **kwargs):
        e = cls.table.query_unique(**kwargs)
        return cls(entity=e) if e else None

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
            self.update(op=UpdateOps.Supported.SET, **self.to_dict())
        else:
            result = self.table.collection.insert_one(self.to_dict())
            self.oid = result.inserted_id

    def update_ex(self, ops):
        assert self.oid
        assert ops and isinstance(ops, UpdateOps)
        d = ops.update
        r = self.table.collection.update_one({OID_KEY: self.oid}, d)
        for op in ops.update:
            for k in d[op]:
                assert k in self.db_fields
                v = d[op][k]
                if op == ops.Supported.SET.value:
                    setattr(self, k, v)
                elif op == ops.Supported.ADD_TO_LIST.value:
                    l = getattr(self, k)
                    assert isinstance(l, list)
                    if v not in l:
                        l.append(v)
                        setattr(self, k, l)
                elif op is ops.Supported.DEL_FROM_LIST.value:
                    l = getattr(self, k)
                    assert isinstance(l, list)
                    if v in l:
                        l.remove(v)
                        setattr(self, k, l)
                else:
                    raise ValueError('Invalid op: {}'.format(op))
        return r.matched_count == 1

    def update(self, op, **kwargs):
        assert self.oid
        return self.update_ex(UpdateOps(op=op, **kwargs))

    def read(self):
        entity = self.table.read(self.oid)
        self.from_entity(entity)

    def delete(self):
        self.table.delete(self.oid)
        self.oid = None


class BasicTable(ABC):
    client = MongoClient(MONGODB_URI)
    db = client[_adjust_mongodb_db_name(MONGODB_DB)]

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
            raise ValueError("{}: ({!r}) must be unique".format(self.collection.name, kwargs))
        for r in results.limit(-1):
            return r
        return None
