import argparse
import os.path
import datetime

idem_path = os.path.join(os.path.expanduser("~"), ".idem")


def full_path(f):
    return os.path.join(idem_path, f)


def mtime(f):
    return os.path.getmtime(full_path(f))


def strformat(time):
    return datetime.datetime.fromtimestamp(time).strftime("%c")


def show_log(args):
    for f in sorted(os.listdir(idem_path), key=mtime):
        print f + "  " + strformat(mtime(f)) + "  " + open(full_path(f)).read().strip()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Ultra-lightweight Python framework for idempotent local provisioning.")
    subparsers = parser.add_subparsers()

    parser_log = subparsers.add_parser("log")  # TODO : help message
    parser_log.set_defaults(func=show_log)

    args = parser.parse_args()
    args.func(args)
