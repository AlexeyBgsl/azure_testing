from .config import CONFIG


def m_link(ref):
    return 'http://m.me/' + CONFIG['FB_PAGE_NAME'] + '?ref=' + ref


class BotRef(object):
    PARAMS_DELIMITER = ';'
    KEYVAL_DELIMITER = ':'

    @classmethod
    def get_ref(cls, **kwargs):
        ref = ''
        for k in kwargs:
            if ref != '':
                ref += cls.PARAMS_DELIMITER
            ref += k + cls.KEYVAL_DELIMITER + kwargs[k]
        return ref

    @classmethod
    def get_params(cls, ref):
        d = {}
        params = ref.split(cls.PARAMS_DELIMITER)
        for p in params:
            v = p.split(cls.KEYVAL_DELIMITER)
            if v and len(v) == 2:
                d[v[0]] = v[1]
        return d

    def __init__(self, ref=None, **kwargs):
        self.params = self.get_params(ref) if ref else {}
        if kwargs:
            self.add_params(**kwargs)

    def add_params(self, **kwargs):
        self.params.update(**kwargs)

    @property
    def ref(self):
        return self.get_ref(**self.params)

    def __str__(self):
        return self.ref


