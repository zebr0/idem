#!/usr/bin/python3 -u

import argparse
import datetime
import hashlib
import os.path
import subprocess
import sys
import urllib.request

# path where the idem files will be stored
idem_path = "/var/idem"

# list of commands that will always be run (no idem file will be created for them)
always_run = ["apt-get update"]


# gets the full path of an idem file
def full_path(f): return os.path.join(idem_path, f)


# gets the mtime of an idem file
def mtime(f): return os.path.getmtime(full_path(f))


# formats given time in a human-readable way
def strformat(time): return datetime.datetime.fromtimestamp(time).strftime("%c")


# turns given text in blue
def blue(string): return '\033[94m' + string + '\033[0m'


# turns given text in green
def green(string): return '\033[92m' + string + '\033[0m'


# turns given text in red
def red(string): return '\033[91m' + string + '\033[0m'


# represents a command about to be executed
class Command:
    def __init__(self, command):
        self.command = command  # the command itself
        self.hash = hashlib.md5(command.encode("ascii")).hexdigest()  # its md5 hash
        self.always_run = any(filter(lambda a: a in self.command, always_run))  # is it always supposed to be run ?

    # has the command ever been run before ?
    def todo(self):
        return not os.path.isfile(full_path(self.hash))

    # prints the command's status, whether it will be executed or not
    def dryrun(self):
        print((blue("always") if self.always_run else blue("  todo") if self.todo() else green("  done")), self.command)

    # executes the command if it hasn't been executed yet
    # in "step" mode, asks confirmation before running each step
    def run(self, step):
        if self.always_run or self.todo():
            if step:
                print(blue("next:"), self.command)
                print(blue("(e)xecute"), green("(s)kip"), red("(a)bort ?"))

                choice = sys.stdin.readline().strip()
                if choice == "e":
                    print(blue("executing"))
                elif choice == "s":
                    print(green("skipped"))
                    return
                else:
                    print(red("aborting"))
                    exit(0)
            else:
                print(blue("executing"), self.command)

            # opens a subshell to execute the command, and prints stdout and stderr lines as they come
            sp = subprocess.Popen(self.command, shell=True, stdout=sys.stdout, stderr=sys.stderr)
            sp.wait()

            # if the run is successful...
            if sp.returncode == 0:
                # and the command only has to be run once...
                if not self.always_run:
                    # then creates an idem file to mark and log the command's execution
                    with open(full_path(self.hash), "w") as f:
                        f.writelines(self.command)
                print(green("done"))
            else:
                print(red("error"))
                exit(1)
        else:
            print(green("skipping"), self.command)


# main function: prints a history of all idem executed commands
def show_log(args):
    if os.path.isdir(idem_path):
        for f in sorted(os.listdir(idem_path), key=mtime):
            with open(full_path(f)) as file:
                print(blue(f), green(strformat(mtime(f))), file.read().strip())


# downloads the commands of a given script in a given version
# with the "include" directive, can do so recursively
def download_commands(script, version):
    # builds the script url and initializes the resulting Commands' list
    url = "https://raw.githubusercontent.com/mazerty/idem/{0}/scripts/{1}.sh".format(version, script)
    commands = []

    # downloads the script and loop through each line
    for line in urllib.request.urlopen(url).read().decode("ascii").splitlines():
        # if the line begins with ##, it may be a directive, so we analyze its words
        if line.startswith("##"):
            split = line.rsplit()

            if split[1] == "include":
                # include directive: recursively downloads the given script's commands and adds them to the list
                commands.extend(download_commands(split[2], version))
            elif split[1] == "resource":
                # resource directive: appends a command that downloads the given file into the /tmp directory
                commands.append(Command(
                    "wget https://raw.githubusercontent.com/mazerty/idem/{0}/resources/{1}/{2} -O /tmp/{2}".format(
                        version, script, split[2])))
            elif split[1] == "template":
                # template directive: similar to "resource" except it executes each {{ block }}
                commands.append(Command(
                    "wget -O- https://raw.githubusercontent.com/mazerty/idem/{0}/resources/{1}/{2} | template.py > /tmp/{2}".format(
                        version, script, split[2])))
        elif not line.startswith("#") and not line == "":
            # it's a standard shell command, appends it to the end of the list
            commands.append(Command(line))

    return commands


# main function: downloads then runs or tests a given script in a given version
def run_script(args):
    # ensures that idem is run as root
    if os.geteuid() != 0:
        print(red("root privileges required to run commands"))
        exit(1)

    # ensures that idem path exists
    if not os.path.isdir(idem_path):
        os.makedirs(idem_path)

    for c in download_commands(args.script, args.version):
        c.dryrun() if args.dry else c.run(args.step)


# entrypoint
if __name__ == '__main__':
    # argumentparser : the best way to handle program arguments in python
    parser = argparse.ArgumentParser(
        description="Lightweight Python-Shell framework for idempotent local provisioning.")
    subparsers = parser.add_subparsers()

    parser_log = subparsers.add_parser("log", help="prints a history of all idem.py executed commands")
    parser_log.set_defaults(func=show_log)

    parser_run = subparsers.add_parser("run", help="downloads then runs or tests a given script in a given version")
    parser_run.add_argument("script", nargs="?", help="script identifier in the repository")
    parser_run.add_argument("version", nargs="?", default="master", help="repository branch or tag (default: master)")
    parser_run.add_argument("--dry", action="store_true", help="tests the script instead of running it")
    parser_run.add_argument("--step", action="store_true", help="asks confirmation before running each step")
    parser_run.set_defaults(func=run_script)

    args = parser.parse_args()
    args.func(args)
