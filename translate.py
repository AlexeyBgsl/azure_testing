import argparse
from bot import String, StringId


def sid_name(sid):
    for s in StringId:
        if s.value == int(sid):
            return s.name
    return 'Unknown'


def print_string(s):
    print('String#{oid} {sid}'.format(oid=s.oid, sid=sid_name(s.sid)))
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
                    choices=['list', 'show', 'set', 'remove'])
parser.add_argument("-s", "--sid", help="String ID")
parser.add_argument("-l", "--lang", help="language")
parser.add_argument("-t", "--text", help="text")

args = parser.parse_args()

if args.command == 'list':
    results = String.all()
    print('Following strings are in table')
    for s in results:
        print_string(s)
else:
    if not args.sid:
        raise ValueError("Please specify String ID")

    sid = int_val(args.sid)
    if sid:
        if sid <= StringId.SID_NONE.value:
            raise ValueError(
                "String ID must be greater than {}".format(StringId.SID_NONE))
        elif sid >= StringId.SID_LAST.value:
            raise ValueError(
                "String ID must be less than {}".format(StringId.SID_LAST))

        print("Setting " + sid_name(sid))
    else:
        for s in StringId:
            if s.name == args.sid:
                if args.sid == StringId.SID_NONE.name or \
                                args.sid == StringId.SID_LAST.name:
                    raise ValueError(
                        "Invalid String ID {}".format(args.sid))
                sid = s.value
                break

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
