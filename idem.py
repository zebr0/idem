#!/usr/bin/python3 -u

import argparse
import configparser
import datetime
import hashlib
import os.path
import subprocess
import sys
import urllib.request


# formats given time in a human-readable way
def strformat(time): return datetime.datetime.fromtimestamp(time).strftime("%c")


# turns given text in blue
def blue(string): return '\033[94m' + string + '\033[0m'


# turns given text in green
def green(string): return '\033[92m' + string + '\033[0m'


# turns given text in red
def red(string): return '\033[91m' + string + '\033[0m'


# handles idem configuration
class Configuration:
    def __init__(self):
        # reads the configuration file first from /etc then from the working directory if present
        parser = configparser.ConfigParser()
        parser.read(["/etc/idem.conf", "idem.conf"])

        # base url for idem scripts and resources (mandatory in config file)
        self._base_url = parser.get("config", "base_url")

        # path where the idem files will be stored
        self._idem_path = parser.get("config", "idem_path", fallback="/var/idem")

        # list of commands that will always be run (no idem file will be created for them)
        self._always_run = parser.get("config", "always_run", fallback="apt-get update").split(";")

    def get_resource_url(self): return self._base_url + "/resources/{0}/{1}"

    # returns the formatted command to download a given resource for a given script
    def get_resource_command(self, script, resource):
        return ("wget " + self.get_resource_url() + " -O /tmp/{1}").format(script, resource)

    # returns the formatted command to download and parse a given template for a given script
    def get_template_command(self, script, template):
        return ("wget -O- " + self.get_resource_url() + " | template.py > /tmp/{1}").format(script, template)

    # returns the url for a given script
    def get_script_url(self, script):
        return (self._base_url + "/scripts/{0}.sh").format(script)

    def get_idem_path(self): return self._idem_path

    # returns the full path of an idem file
    def get_full_path(self, file):
        return os.path.join(self._idem_path, file)

    # returns the mtime of an idem file
    def get_mtime(self, file):
        return os.path.getmtime(self.get_full_path(file))

    def get_always_run(self): return self._always_run


# reads the configuration for the rest of the script
config = Configuration()


# represents a command about to be executed
class Command:
    def __init__(self, command):
        # the command itself
        self._command = command

        # its md5 hash
        self._hash = hashlib.md5(command.encode("ascii")).hexdigest()

        # is it always supposed to be run ?
        self._always_run = any(filter(lambda a: a in self._command, config.get_always_run()))

    # has the command ever been run before ?
    def todo(self):
        return not os.path.isfile(config.get_full_path(self._hash))

    # prints the command's status, whether it will be executed or not
    def dryrun(self):
        print((blue("always") if self._always_run else blue("  todo") if self.todo() else green("  done")),
              self._command)

    # executes the command if it hasn't been executed yet
    # in "step" mode, asks confirmation before running each step
    def run(self, step):
        if self._always_run or self.todo():
            if step:
                print(blue("next:"), self._command)
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
                print(blue("executing"), self._command)

            # opens a subshell to execute the command, and prints stdout and stderr lines as they come
            sp = subprocess.Popen(self._command, shell=True, stdout=sys.stdout, stderr=sys.stderr)
            sp.wait()

            # if the run is successful...
            if sp.returncode == 0:
                # and the command only has to be run once...
                if not self._always_run:
                    # then creates an idem file to mark and log the command's execution
                    with open(config.get_full_path(self._hash), "w") as file:
                        file.writelines(self._command)
                print(green("done"))
            else:
                print(red("error"))
                exit(1)
        else:
            print(green("skipping"), self._command)


# downloads the commands of a given script
# with the "include" directive, can do so recursively
def download_commands(script):
    # initializes the resulting Commands' list
    commands = []

    # downloads the script and loop through each line
    for line in urllib.request.urlopen(config.get_script_url(script)).read().decode("ascii").splitlines():
        # if the line begins with ##, it may be a directive, so we analyze its words
        if line.startswith("##"):
            split = line.rsplit()

            if split[1] == "include":
                # include directive: recursively downloads the given script's commands and adds them to the list
                commands.extend(download_commands(split[2]))
            elif split[1] == "resource":
                # resource directive: appends a command that downloads the given file into the /tmp directory
                commands.append(Command(config.get_resource_command(script, split[2])))
            elif split[1] == "template":
                # template directive: similar to "resource" except it executes each {{ block }}
                commands.append(Command(config.get_template_command(script, split[2])))
        elif not line.startswith("#") and not line == "":
            # it's a standard shell command, appends it to the end of the list
            commands.append(Command(line))

    return commands


# main function: prints a history of all idem executed commands
def show_log(args):
    if os.path.isdir(config.get_idem_path()):
        for f in sorted(os.listdir(config.get_idem_path()), key=config.get_mtime):
            with open(config.get_full_path(f)) as file:
                print(blue(f), green(strformat(config.get_mtime(f))), file.read().strip())


# main function: downloads then runs or tests a given script
def run_script(args):
    # ensures that idem is run as root
    if os.geteuid() != 0:
        print(red("root privileges required to run commands"))
        exit(1)

    # ensures that idem path exists
    if not os.path.isdir(config.get_idem_path()):
        os.makedirs(config.get_idem_path())

    for c in download_commands(args.script):
        c.dryrun() if args.dry else c.run(args.step)


# entrypoint
if __name__ == '__main__':
    # argumentparser : the best way to handle program arguments in python
    argparser = argparse.ArgumentParser(
        description="Lightweight Python-Shell framework for idempotent local provisioning.")
    subparsers = argparser.add_subparsers()

    parser_log = subparsers.add_parser("log", help="prints a history of all idem.py executed commands")
    parser_log.set_defaults(func=show_log)

    parser_run = subparsers.add_parser("run", help="downloads then runs or tests a given script")
    parser_run.add_argument("script", nargs="?", help="script identifier in the repository")
    parser_run.add_argument("--dry", action="store_true", help="tests the script instead of running it")
    parser_run.add_argument("--step", action="store_true", help="asks confirmation before running each step")
    parser_run.set_defaults(func=run_script)

    args = argparser.parse_args()
    args.func(args)
