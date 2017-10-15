import logging
from datetime import timedelta
from db import DCRS


class Horn():
    def __init__(self, page):
        self.page = page

    def notify_one(self, user, annc, channel=None):
        if not channel:
            channel = DCRS.Channels.by_oid(annc.chid)
            if not channel:
                raise ValueError("Annc#{} belongs to nonexistent channel#{}".format(
                        annc.oid, annc.chid))

        created = timedelta(hours=user.timezone) + annc.created
        date = created.strftime("%B %d, %Y")
        time = created.strftime("%I:%M %p")
        message = ("// {chname}\n"
                   "\n{text}\n\n"
                   "// {time} // {date}").format(chname=channel.name,
                                                 text=annc.text,
                                                 time=time,
                                                 date=date)
        self.page.send(user.fbid, message)

    def notify(self, annc, decorate=True, skip_owner=False):
        c = DCRS.Channels.by_oid(annc.chid)
        if c:
            subs = c.subs
            if not skip_owner and annc.owner_uid not in c.subs:
                subs.insert(0, annc.owner_uid)
            for uid in subs:
                u = DCRS.Users.by_oid(uid)
                if u:
                    if decorate:
                        self.notify_one(user=u, annc=annc, channel=c)
                    else:
                        self.page.send(u.fbid, annc.text)
                else:
                    logging.debug("[C#%s] nonexistent user subscribed (%s)?",
                                  annc.chid, uid)
        else:
            logging.debug("[A#%s] is made on nonexistent channel (%s)?",
                          annc.oid, annc.chid)


