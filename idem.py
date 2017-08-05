import argparse
import datetime
import hashlib
import os.path
import subprocess
import urllib2

idem_path = os.path.join(os.path.expanduser("~"), ".idem")
always_run = ["apt-get update"]


def full_path(f): return os.path.join(idem_path, f)


def mtime(f): return os.path.getmtime(full_path(f))


def strformat(time): return datetime.datetime.fromtimestamp(time).strftime("%c")


def blue(string): return '\033[94m' + string + '\033[0m'


def green(string): return '\033[92m' + string + '\033[0m'


class Command:
    def __init__(self, command):
        self.command = command
        self.hash = hashlib.md5(command).hexdigest()
        self.todo = not os.path.isfile(full_path(self.hash))
        self.always_run = any(filter(lambda a: a in self.command, always_run))

    def dryrun(self):
        print (blue("always") if self.always_run else blue("  todo") if self.todo else green("  done")) \
              + " " + self.command

    def run(self):
        if self.always_run or self.todo:
            print blue("executing ") + self.command

            sp = subprocess.Popen(self.command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            for line in iter(sp.stdout.readline, b''):
                print " " + line.strip()
            sp.wait()

            if sp.returncode == 0:
                if not self.always_run:
                    f = open(full_path(self.hash), "w")
                    f.writelines(self.command)
                    f.close()
                print green("done")
            else:
                raise Exception
        else:
            print green("skipping ") + self.command


def show_log(args):
    for f in sorted(os.listdir(idem_path), key=mtime):
        print green(strformat(mtime(f))) + " " + open(full_path(f)).read().strip()


def download_commands(script, version, recursionsafe=set()):
    if script in recursionsafe:
        raise Exception
    else:
        recursionsafe.add(script)

    url = "https://raw.githubusercontent.com/mazerty/idem/{0}/script/{1}.sh".format(version, script)
    commands = []

    for command in urllib2.urlopen(url).read().splitlines():
        if command.startswith("#"):
            split = command.rsplit()
            if split[1] == "include":
                commands.extend(download_commands(split[2], version, recursionsafe))
        else:
            commands.append(Command(command))

    return commands


def dryrun_script(args):
    for c in download_commands(args.script, args.version):
        c.dryrun()


def run_script(args):
    for c in download_commands(args.script, args.version):
        c.run()


if __name__ == '__main__':
    if not os.path.isdir(idem_path):
        os.makedirs(idem_path)

    parser = argparse.ArgumentParser(
        description="Ultra-lightweight Python framework for idempotent local provisioning.")
    subparsers = parser.add_subparsers()

    parser_log = subparsers.add_parser("log")  # TODO : help message
    parser_log.set_defaults(func=show_log)

    parser_dryrun = subparsers.add_parser("dryrun")
    parser_dryrun.add_argument("script", nargs="?")
    parser_dryrun.add_argument("version", nargs="?", default="master")
    parser_dryrun.set_defaults(func=dryrun_script)

    parser_run = subparsers.add_parser("run")
    parser_run.add_argument("script", nargs="?")
    parser_run.add_argument("version", nargs="?", default="master")
    parser_run.set_defaults(func=run_script)

    args = parser.parse_args()
    args.func(args)
