import argparse
import datetime
import os.path
import urllib2

idem_path = os.path.join(os.path.expanduser("~"), ".idem")


def full_path(f):
    return os.path.join(idem_path, f)


def mtime(f):
    return os.path.getmtime(full_path(f))


def strformat(time):
    return datetime.datetime.fromtimestamp(time).strftime("%c")


def show_log(args):
    for f in sorted(os.listdir(idem_path), key=mtime):
        print(f + "  " + strformat(mtime(f)) + "  " + open(full_path(f)).read().strip())


def get_commands(args):
    return map(lambda l: l.strip(),
               urllib2.urlopen("https://raw.githubusercontent.com/mazerty/idem/{0}/script/{1}.sh"
                               .format(args.version, args.script)).readlines())


def dryrun_script(args):
    print(get_commands(args))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Ultra-lightweight Python framework for idempotent local provisioning.")
    subparsers = parser.add_subparsers()

    parser_log = subparsers.add_parser("log")  # TODO : help message
    parser_log.set_defaults(func=show_log)

    parser_dryrun = subparsers.add_parser("dryrun")
    parser_dryrun.add_argument("script", nargs="?")
    parser_dryrun.add_argument("version", nargs="?", default="master")
    parser_dryrun.set_defaults(func=dryrun_script)

    args = parser.parse_args()
    args.func(args)
