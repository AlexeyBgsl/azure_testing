import re
from db import BasicEntry, BasicTable, safe_db_access


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


@safe_db_access
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


@safe_db_access
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
