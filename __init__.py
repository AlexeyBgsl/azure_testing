from .models import User, Channel, Annc, String, \
    Users, Channels, Anncs, Strings, \
    update_defaults_models as _update_defaults_models
from .blob import FileStorage, \
    update_default_file_storage as _update_default_file_storage
from .mongodb import UpdateOps
from .config import DataCenterResourceSet, DCRS, store_config as _store_config
from .misc import m_link, BotRef


def config(values):
    _store_config(values)
    _update_defaults_models()
    _update_default_file_storage()

