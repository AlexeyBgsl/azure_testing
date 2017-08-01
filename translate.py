import argparse
import glob
import os
from bot import BotString


def print_string(s, verbose=False):
    print('{sid} {db}DB {df}DEF'.format(sid=s.sid,
                                        db = '' if s.in_db else '!',
                                        df='' if s.has_def else '!'))
    if verbose:
        locales = s.list()
        for l in locales:
            print('    {} {}'.format(l, s.get(l)))


def get_identifier(s):
    identifier = ''
    for c in s:
        i = identifier + c
        if i.isidentifier():
            identifier = i
        else:
            break
    return identifier


def sids_by_code():
    path = os.path.dirname(os.path.abspath(__file__))
    files = [file for file in glob.glob(path + '/bot/**/*.py',
                                        recursive=True)]
    sids = []
    for fname in files:
        with open(fname) as f:
            lines = f.readlines()
            for l in lines:
                b = l.find('SID_')
                if b != -1:
                    sid = get_identifier(l[b:])
                    if sid not in sids:
                        sids.append(sid)
    return sids


def check_code(verbose):
    sids = sids_by_code()
    for sid in sids:
        s = BotString(sid)
        print_string(s, verbose=verbose)


parser = argparse.ArgumentParser()
parser.add_argument("command", help="command to execute",
                    choices=['list_db', 'list_ids', 'check', 'fill',
                             'show', 'set', 'remove'])
parser.add_argument("-s", "--sid", help="String ID")
parser.add_argument("-l", "--lang", help="language")
parser.add_argument("-t", "--text", help="text")
parser.add_argument("-v", "--verbose", help="increase output verbosity",
                    action="store_true")
parser.add_argument("-f", "--force", help="force string overriding",
                    action="store_true")

args = parser.parse_args()

verbose = args.verbose if args.verbose else False

if args.command == 'list_db':
    results = String.all()
    print('Following strings are in table:')
    for s in results:
        print_string(s, verbose=verbose)
elif args.command == 'list_ids':
    print('Following String IDs exist:')
    for sid in BotString.all_defaults():
        s = BotString(sid)
        print_string(s, verbose=verbose)
elif args.command == 'check':
    check_code(verbose)
elif args.command == 'fill':
    BotString.default_strings_to_db(override=True if args.force else False)
else:
    if not args.sid:
        raise ValueError("Please specify String ID")

    s = BotString(args.sid)

    if args.command == 'show':
        print_string(s, verbose=verbose)
    elif args.command == 'set':
        if not args.lang:
            raise ValueError("Please specify Language")
        if not args.text:
            raise ValueError("Please specify Text")
        s.set(args.lang, args.text)
        s.save()
    elif args.command == 'remove':
        s.delete()
    else:
        raise ValueError("Unknown command")
