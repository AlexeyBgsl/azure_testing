import os
import requests
from io import BytesIO
from azure.storage.blob import BlockBlobService, ContentSettings
from azure.common import AzureHttpError
from .config import STORAGE_ACCOUNT_NAME, STORAGE_ACCOUNT_KEY


class FileStorage(object):
    service = BlockBlobService(account_name=STORAGE_ACCOUNT_NAME,
                               account_key=STORAGE_ACCOUNT_KEY)

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

    @classmethod
    def dir(cls, type):
        return [blob.name for blob in cls.service.list_blobs(type)]

    @classmethod
    def get_url(cls, type, fname):
        return cls.service.make_blob_url(type, fname)

    @classmethod
    def upload(cls, local_fname, type, fname, content_type=None):
        if content_type:
            ctx = ContentSettings(content_type=content_type)
        else:
            ctx = cls.content_by_fname(local_fname)
        cls.service.create_blob_from_path(type,
                                          fname,
                                          local_fname,
                                          content_settings=ctx)

    @classmethod
    def download(cls, type, fname, local_fname):
        cls.service.get_blob_to_path(type, fname, local_fname)

    @classmethod
    def upload_from_url(cls, url, type, fname):
        with requests.get(url, stream=True) as r:
            ctx = cls.content_by_responce(r)
            cls.service.create_blob_from_stream(type, fname,
                                                stream=BytesIO(r.content),
                                                content_settings=ctx)
        return None

    @classmethod
    def remove(cls, type, fname):
        try:
            cls.service.delete_blob(type, fname)
        except AzureHttpError:
            pass
