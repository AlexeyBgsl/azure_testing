import argparse
from bot import String, StringId


def normalized_sid_name(sid_name):
    if StringId.from_sid_name(sid_name):
        return sid_name
    return '*' + sid_name


def print_string(s):
    print('{sid} {oid:015d}'.format(sid=normalized_sid_name(s.sid), oid=s.oid))
    locales = s.list()
    for l in locales:
        print('    {} {}'.format(l, s.get(l)))


def int_val(s):
    try:
        return int(s)
    except ValueError:
        return None


parser = argparse.ArgumentParser()
parser.add_argument("command", help="command to execute",
                    choices=['list_db', 'list_ids', 'check', 'fill',
                             'show', 'set', 'remove'])
parser.add_argument("-s", "--sid", help="String ID")
parser.add_argument("-l", "--lang", help="language")
parser.add_argument("-t", "--text", help="text")

args = parser.parse_args()

if args.command == 'list_db':
    results = String.all()
    print('Following strings are in table:')
    for s in results:
        print_string(s)
elif args.command == 'list_ids':
    print('Following String IDs exist:')
    for sid in StringId:
        s = String(sid)
        print_string(s)
elif args.command == 'check':
    StringId.check_default_strings()
elif args.command == 'fill':
    StringId.default_strings_to_db()
else:
    if not args.sid:
        raise ValueError("Please specify String ID")

    if not StringId.is_valid(args.sid):
        raise ValueError(
            "Invalid String ID {}".format(args.sid))

    if args.command == 'show':
        s = String(args.sid)
        print_string(s)
    elif args.command == 'set':
        if not args.lang:
            raise ValueError("Please specify Language")
        if not args.text:
            raise ValueError("Please specify Text")
        s = String(args.sid)
        s.set(args.lang, args.text)
        s.save()
    elif args.command == 'remove':
        s = String(args.sid)
        s.delete()
    else:
        raise ValueError("Unknown command")
