import os
import requests
from io import BytesIO
from azure.storage.blob import BlockBlobService, ContentSettings
from azure.common import AzureHttpError
from .config import CONFIG, DCRS


class FileStorage(object):
    @staticmethod
    def content_by_fname(fname):
        root, ext =  os.path.splitext()
        e = ext.lower()
        if e == '.png':
            return ContentSettings(content_type='image/png')
        elif e == '.jpg' or e == '.jpeg':
            return ContentSettings(content_type='image/jpeg')
        return None

    @staticmethod
    def content_by_responce(r):
        ct = r.headers.get('Content-Type', None)
        return ContentSettings(content_type=ct) if ct else None

    def __init__(self, account_name, account_key):
        self.service = BlockBlobService(account_name=account_name,
                                        account_key=account_key)

    def dir(self, type):
        return [blob.name for blob in self.service.list_blobs(type)]

    def get_url(self, type, fname):
        return self.service.make_blob_url(type, fname)

    def upload(self, local_fname, type, fname, content_type=None):
        if content_type:
            ctx = ContentSettings(content_type=content_type)
        else:
            ctx = self.content_by_fname(local_fname)
            self.service.create_blob_from_path(type,
                                               fname,
                                               local_fname,
                                               content_settings=ctx)

    def download(self, type, fname, local_fname):
        self.service.get_blob_to_path(type, fname, local_fname)

    def upload_from_url(self, url, type, fname):
        with requests.get(url, stream=True) as r:
            ctx = self.content_by_responce(r)
            self.service.create_blob_from_stream(type, fname,
                                                 stream=BytesIO(r.content),
                                                 content_settings=ctx)
        return None

    def remove(self, type, fname):
        try:
            self.service.delete_blob(type, fname)
        except AzureHttpError:
            pass


def update_default_file_storage():
    DCRS.set('FileStorage',
             FileStorage(account_key=CONFIG['STORAGE_ACCOUNT_KEY'],
                         account_name=CONFIG['STORAGE_ACCOUNT_NAME']))
