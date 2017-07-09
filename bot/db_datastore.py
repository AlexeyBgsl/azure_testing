from abc import ABC
from google.cloud import datastore
from bot.config import CONFIG

# See https://googlecloudplatform.github.io/google-cloud-python/stable/datastore-client.html

builtin_list = list


def from_datastore(entity):
    """Translates Datastore results into the format expected by the
    application.

    Datastore typically returns:
        [Entity{key: (kind, id), prop: val, ...}]

    This returns:
        {id: id, prop: val, ...}
    """
    if not entity:
        return None
    if isinstance(entity, builtin_list):
        entity = entity.pop()

    entity['id'] = entity.key.id
    return entity


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
        return from_datastore(entity)

    def update(self, data, oid):
        return self._update(data, oid)

    def create(self, data):
        return self.update(data, None)

    def read(self, oid):
        results = self.client.get(self._get_key(oid))
        return from_datastore(results)

    def delete(self, oid):
        self.client.delete(self._get_key(oid))

    def query(self):
        return self.client.query(kind=self.kind)


class Users(BasicTable):
    def __init__(self):
        super().__init__(kind="Users")

    def by_fbid(self, fbid):
        query = self.query()
        query.add_filter('fbid', '=', fbid)
        results = list(query.fetch())
        if len(results) > 1:
            raise ValueError("FB ID must be unique")
        return results[0] if results else None
