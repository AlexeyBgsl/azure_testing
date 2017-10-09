import argparse
from db import DCRS, UpdateOps
from bot.chat import BotRef
import requests
from config import CONFIG
from db import config as db_config
import xml.etree.ElementTree as ET


def setup_rel_env(config):
    rel_config = config
    tree = ET.parse('web.config')
    root = tree.getroot()
    print("Setting up the Release environment\n")
    for child in root:
        if child.tag == 'appSettings':
            for k in child.iter('add'):
                print("\t{} = {}\n".format(k.attrib['key'], k.attrib['value']))
                rel_config[k.attrib['key']] = k.attrib['value']
            return rel_config
    raise ValueError("Cannot find release config values")


def reset_test_bot():
    print("Resetting test bot ({})\n".format(CONFIG['FB_PAGE_NAME']))
    for u in DCRS.Users.all():
        print("Deleting user {} ({})\n".format(u.fbid, u.oid))
        u.delete()


def exists(path):
    print("Checking {}\n".format(path))
    r = requests.head(path)
    return r.status_code == requests.codes.ok


def fix_qr_code():
    for c in DCRS.Channels.all():
        if not c.qr_code or not exists(c.qr_code):
            print("Fixing QR Code for channel#{} ({})".format(c.oid, c.uchid))
            r = BotRef(sub=c.uchid)
            c.set_code(ref=r.ref)


def cleanup_anncs():
    for a in DCRS.Anncs.all():
        c = DCRS.Channels.by_oid(a.chid)
        if not c:
            print("Deleting Anncs#{}\n".format(a.oid))
            a.delete()


def fix_anncs():
    for a in DCRS.Anncs.all():
        if hasattr(a, 'title'):
            print("Fixing Title for Annc#{}\n".format(a.oid))
            new_text = a.title + '\n\n' + a.text
            opts = UpdateOps()
            opts.add(UpdateOps.Supported.SET, text=new_text)
            opts.add(UpdateOps.Supported.DEL, title='')
            if opts.has_update:
                a.update_ex(opts)
        if len(a.text) > BotPage.MAX_TEXT_LEN:
            print("Annc#{}: Text is too long, removing\n".format(a.oid))
            a.delete()


parser = argparse.ArgumentParser()
parser.add_argument("--reset-dbg", help="Reset Debug Bot",
                    action="store_true")
parser.add_argument("--fix-qr", help="Fix QR Codes",
                    action="store_true")
parser.add_argument("--cleanup_anncs", help="Cleanup Announcements",
                    action="store_true")
parser.add_argument("--fix-annc-title", help="Fix Announcement title",
                    action="store_true")
parser.add_argument("--fix-annc", help="Fix Announcements",
                    action="store_true")
parser.add_argument("--all", help="Fix Everything",
                    action="store_true")


args = parser.parse_args()


db_config(CONFIG)
if args.all or args.reset_dbg:
    reset_test_bot()

rel_config = setup_rel_env(CONFIG)
db_config(rel_config)
if args.all or args.fix_qr:
    fix_qr_code()
if args.all or args.cleanup_anncs:
    cleanup_anncs()
if args.all or args.fix_annc:
    fix_anncs()
