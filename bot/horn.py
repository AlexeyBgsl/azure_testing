import logging
from db import User, Channel
from bot.translations import BotString


class Horn():
    def __init__(self, page):
        self.page = page

    def notify(self, annc):
        c = Channel.by_chid(annc.chid)
        if c:
            for uid in c.subs:
                u = User.by_oid(uid)
                if u:
                    message = str(BotString('SID_ANNC_MESSAGE',
                                            user=u,
                                            channel=c,
                                            annc=annc))
                    self.page.send(u.fbid, message)
                else:
                    logging.debug("[C#%s] nonexistent user subscribed (%s)?",
                                  annc.chid, uid)
        else:
            logging.debug("[A#%s] is made on nonexistent channel (%s)?",
                          annc.oid, annc.chid)


