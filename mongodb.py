from abc import ABC
from enum import Enum
from pymongo import MongoClient
from bson.objectid import ObjectId


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
        DEL = '$unset'
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
    INIT_FIELDS = None

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

    def __init__(self, table, **kwargs):
        assert table
        assert self.INIT_FIELDS
        self.table = table
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
            self.oid = self.table.insert(self)

    def save_unique(self, **kwargs):
        assert self.oid is None
        assert kwargs
        self.oid = self.table.insert_or_update(kwargs, self)

    def update_ex(self, ops):
        assert self.oid
        assert ops and isinstance(ops, UpdateOps)
        d = ops.update
        r = self.table.update(self, d)
        for op in ops.update:
            for k in d[op]:
                assert k in self.db_fields
                v = d[op][k]
                if op == ops.Supported.SET.value:
                    setattr(self, k, v)
                elif op is ops.Supported.DEL.value:
                    delattr(self, k)
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
    obj_type = None

    def __page_dict(self, d):
        d['fbpage'] = self.fb_page_name
        return d

    def __init__(self, mongodb_uri, db_name, col_name, fb_page_name):
        assert type(self).obj_type
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[_adjust_mongodb_db_name(db_name)]
        self.collection = self.db[col_name]
        self.fb_page_name = fb_page_name

    def insert_or_update(self, filter, obj):
        assert obj.oid is None
        u = UpdateOps(op=UpdateOps.Supported.SET,
                      **self.__page_dict(obj.to_dict()))
        result = self.collection.update_one(self.__page_dict(filter),
                                            u.update,
                                            upsert=True)
        return result.upsertedId

    def insert(self, entry):
        assert entry.oid is None
        result = self.collection.insert_one(self.__page_dict(entry.to_dict()))
        return result.inserted_id

    def by_oid(self, oid):
        assert oid
        if isinstance(oid, str):
            oid = ObjectId(oid)
        e = self.collection.find_one({OID_KEY: oid})
        return self.obj_type(table=self, entity=e) if e else None

    def delete(self, oid):
        self.collection.find_one_and_delete({OID_KEY: oid})

    def update(self, obj, update):
        return self.collection.update_one(
            self.__page_dict({OID_KEY: obj.oid}),
            update)

    def raw_find(self, **kwargs):
        return list(self.collection.find(self.__page_dict(kwargs)))

    def raw_find_unique(self, **kwargs):
        results = self.collection.find(self.__page_dict(kwargs))
        if results.count() > 1:
            raise ValueError("{}: {}: ({!r}) must be unique".format(
                self.fb_page_name, self.collection.name, kwargs))
        for r in results.limit(-1):
            return r
        return None

    def find(self, **kwargs):
        return [self.obj_type(table=self, entity=e)
                for e in self.raw_find(**kwargs)]

    def find_unique(self, **kwargs):
        r = self.raw_find_unique(**kwargs)
        return self.obj_type(table=self, entity=r) if r else None

    def all(self):
        return self.find()

    def new(self, **kwargs):
        return self.obj_type(table=self, **kwargs)
