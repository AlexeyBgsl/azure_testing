import logging
from datetime import timedelta
from db import User, Channel
from bot.translations import BotString


class Horn():
    def __init__(self, page):
        self.page = page

    def notify_one(self, user, annc, channel=None):
        if not channel:
            channel = Channel.by_oid(annc.chid)
            if not channel:
                raise ValueError("Annc#{} belongs to nonexistent channel#{}".format(
                        annc.oid, annc.chid))

        created = timedelta(hours=user.timezone) + annc.created
        date = created.strftime("%B %d, %Y")
        time = created.strftime("%I:%m %p")
        message = ("// {chname}\n"
                   "{title}\n\n"
                   "{text}\n"
                   "// {time} // {date}").format(chname=channel.name,
                                                 title=annc.title,
                                                 text=annc.text,
                                                 time=time,
                                                 date=date)
        self.page.send(user.fbid, message)

    def notify(self, annc):
        c = Channel.by_oid(annc.chid)
        if c:
            for uid in c.subs:
                u = User.by_oid(uid)
                if u:
                    self.notify_one(user=u, annc=annc, channel=c)
                else:
                    logging.debug("[C#%s] nonexistent user subscribed (%s)?",
                                  annc.chid, uid)
        else:
            logging.debug("[A#%s] is made on nonexistent channel (%s)?",
                          annc.oid, annc.chid)


