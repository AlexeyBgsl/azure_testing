import fbmq
import logging
import argparse
from datetime import datetime
from config import CONFIG
from db import BotRef, DCRS, UpdateOps, config as db_config
from bot.config import ACCESS_TOKEN_PRD
from bot.horn import Horn
import xml.etree.ElementTree as ET


def get_page():
    return fbmq.Page(ACCESS_TOKEN_PRD)


class Args():
    def __init__(self, args):
        self.args = args
        self.channel = None
        if args.chid and args.uchid:
            raise ValueError("Conflicting Channel ID parameters: " \
                             "chid={} uchid={}".format(args.chid,
                                                       args.uchid))
        elif args.chid:
            self.channel = DCRS.Channels.by_oid(args.chid)
        elif args.uchid:
            self.channel = DCRS.Channels.find_unique(uchid=args.uchid)

        self.user = None
        if args.uid and args.fbid:
            raise ValueError("Conflicting User ID parameters: " \
                             "uid={} fbid={}".format(args.uid,
                                                     args.fbid))
        elif args.uid:
            self.user = DCRS.Users.by_oid(args.uid)
        elif args.fbid:
            self.user = DCRS.Users.find_unique(fbid=args.fbid)

        self.annc = None
        if args.aid:
            self.annc = DCRS.Anncs.by_oid(args.aid)


def _print_db_entry(entry):
    print("\t{0:10}: {1}".format('type', type(entry).__name__))
    print("\t{0:10}: {1}".format('OID', entry.oid))
    for f in entry.db_fields:
        print("\t{0:10}: {1}".format(f, getattr(entry, f)))
    print("")


def print_db_entries_list(l):
    print("{} objects found".format(len(l)))
    for c in l:
        _print_db_entry(c)


def _set_channel_field(args, fname):
    if not args.channel:
        raise ValueError("Channel is required")
    if not hasattr(args.args, fname):
        raise ValueError("Channel {} is required", fname)
    setattr(args.channel, fname, getattr(args.args, fname))
    args.channel.save()
    print("Done")
    _print_db_entry(args.channel)


def setup_rel_env(config):
    rel_config = config
    tree = ET.parse('web.config')
    root = tree.getroot()
    logging.info("Setting up the Release environment")
    for child in root:
        if child.tag == 'appSettings':
            for k in child.iter('add'):
                logging.debug("\t{} = {}\n".format(
                    k.attrib['key'], k.attrib['value']))
                rel_config[k.attrib['key']] = k.attrib['value']
            return rel_config
    raise ValueError("Cannot find release config values")


def list_channels(args):
    if args.user:
        channels = DCRS.Channels.find(owner_uid=args.user.oid)
    else:
        channels = DCRS.Channels.all()
    print_db_entries_list(channels)


def add_channel(args):
    if not args.args.name:
        raise ValueError("Channel Name is required")
    if not args.args.desc:
        raise ValueError("Channel Description is required")
    if not args.user:
        raise ValueError("User is required")

    c = DCRS.Channels.new(name=args.args.name,
                          owner_uid=args.user.oid)
    r = BotRef(sub=c.uchid)
    mc = get_page().get_messenger_code(ref=r.ref)
    c.set_code(ref=r.ref, messenger_code_url=mc)
    c.desc = args.args.desc
    c.save()
    print("Done")
    _print_db_entry(c)


def del_channel(args):
    if not args.channel:
        raise ValueError("Channel is required")
    chid = input("Enter channel OID to proceed: ")
    if str(args.channel.oid) == chid:
        args.channel.delete()
        print("Done")
    else:
        print("OID mismatch")


def set_channel_name(args):
    _set_channel_field(args, 'name')


def set_channel_decs(args):
    _set_channel_field(args, 'desc')


def set_channel_pic(args):
    _set_channel_field(args, 'pic_url')


def list_anncs(args):
    if args.user and args.channel:
        raise ValueError("Wrong or ambiguous command line")
    if args.user:
        anncs = DCRS.Anncs.find(owner_uid=args.user.oid)
    elif args.channel:
        anncs = DCRS.Anncs.find(chid=args.channel.oid)
    else:
        anncs= DCRS.Anncs.all()
    print_db_entries_list(anncs)


def resend_annc(args):
    if not args.annc:
        raise ValueError("Announcement is required")
    Horn(get_page()).notify(annc=args.annc)
    print("Done")


def add_annc(args):
    if not args.args.text:
        raise ValueError("Announcement text is required")
    if args.user:
        raise ValueError("Wrong or ambiguous command line")
    if not args.channel:
        raise ValueError("Channel is required")
    annc = DCRS.Anncs.new(text=args.args.text,
                          chid=args.channel.oid,
                          owner_uid=args.channel.owner_uid)
    annc.save()
    Horn(get_page()).notify(annc)
    print("Done")
    _print_db_entry(annc)


def del_annc(args):
    if not args.annc:
        raise ValueError("Announcement is required")
    aid = input("Enter Announcemnt OID to proceed: ")
    if str(args.anncs.oid) == aid:
        args.annc.delete()
        print("Done")
    else:
        print("OID mismatch")


def set_annc_text(args):
    if not args.args.text:
        raise ValueError("Announcement text is required")
    if not args.annc:
        raise ValueError("Announcement is required")
    args.annc.text = args.args.text
    args.annc.save()
    print("Done")
    _print_db_entry(args.annc)


def set_annc_dtime(args):
    if not args.args.datetime:
        raise ValueError("Announcement new datetime is required")
    if not args.annc:
        raise ValueError("Announcement is required")
    try:
        d = datetime.strptime(args.args.datetime, '%b %d %Y %I:%M%p')
    except:
        raise ValueError("Invalid datetime: {}".format(args.args.datetime))
    args.annc.created = d
    args.annc.save()
    print("Done")
    _print_db_entry(args.annc)


def list_users(args):
    if args.user or args.channel or args.annc:
        raise ValueError("Wrong or ambiguous command line")
    print_db_entries_list(DCRS.Users.all())


commands = [list_channels, add_channel, del_channel,
            set_channel_name, set_channel_decs, set_channel_pic,
            list_anncs, resend_annc, add_annc, del_annc,
            set_annc_text, set_annc_dtime,
            list_users]


parser = argparse.ArgumentParser()
parser.add_argument("command", help="command to execute",
                    choices=[f.__name__ for f in commands])
parser.add_argument("-c", "--chid", help="Channel Object ID")
parser.add_argument("-uc", "--uchid", help="Channel Human Readable ID (9 cyphers)")
parser.add_argument("-u", "--uid", help="User Object ID")
parser.add_argument("-f", "--fbid", help="Facebook User ID")
parser.add_argument("-a", "--aid", help="Announcement Object ID")
parser.add_argument("-v", "--verbose", help="Be verbose", action='count')
parser.add_argument("-n", "--name", help="Channel Name")
parser.add_argument("-d", "--desc", help="Channel Desc")
parser.add_argument("-p", "--pic_url", help="Channel Picture URL")
parser.add_argument("-t", "--text", help="Announcement Text")
parser.add_argument("--datetime", help="Date and time like: Jun 1 2005 1:33PM")


raw_args = parser.parse_args()

if raw_args.verbose:
    logger = logging.getLogger()
    if raw_args.verbose == 1:
        logger.setLevel(logging.INFO)
    elif raw_args.verbose == 2:
        logger.setLevel(logging.DEBUG)


cmd_func = None

for f in commands:
    if f.__name__ == raw_args.command:
        cmd_func = f
        break

if cmd_func:
    rel_config = setup_rel_env(CONFIG)
    db_config(rel_config)
    args = Args(raw_args)
    cmd_func(args)
else:
    raise ValueError("Unknown command: {}", raw_args.command)
