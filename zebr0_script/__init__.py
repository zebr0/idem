import datetime
import hashlib
import os.path
import pathlib
import subprocess
import sys
import time

import yaml


# formats given time in a human-readable way
def strformat(timestamp): return datetime.datetime.fromtimestamp(timestamp).strftime("%c")


# colors given text in blue
def blue(string): return "\033[94m" + string + "\033[0m"


# colors given text in yellow
def yellow(string): return "\033[93m" + string + "\033[0m"


# colors given text in green
def green(string): return "\033[92m" + string + "\033[0m"


# colors given text in red
def red(string): return "\033[91m" + string + "\033[0m"


# returns the full path of a history file
def get_full_path(file, directory): return os.path.join(directory, file)


# returns the mtime of a history file
def get_mtime(file, directory): return os.path.getmtime(get_full_path(file, directory))


# main function: prints a history of all executed commands
def history(directory):
    def _get_mtime(_file):
        return get_mtime(_file, directory)

    if os.path.isdir(directory):
        for filename in sorted(os.listdir(directory), key=_get_mtime):
            with open(get_full_path(filename, directory)) as file:
                print(blue(filename), green(strformat(get_mtime(filename, directory))), file.read().strip())


# main function: downloads then processes a given script
def run(script, directory, dry, step, client):
    # ensures that history path exists
    if not os.path.isdir(directory):
        os.makedirs(directory)

    [task.handle() for task in recursive_lookup(script, directory, dry, step, client)]


def recursive_lookup(script, directory, dry, step, client):
    for command in yaml.load(client.lookup(script), Loader=yaml.BaseLoader):
        if isinstance(command, str):
            yield Command(command, directory, dry, step, client)
        elif isinstance(command, dict) and command.get("include"):
            yield from recursive_lookup(command.get("include"), directory, dry, step, client)
        elif isinstance(command, dict) and command.get("lookup") and command.get("path"):
            yield Lookup(command, directory, dry, step, client)
        else:
            print(yellow("unknown command, ignored:"), command)


class Task:
    def __init__(self, command, directory, dry, step, client):
        self.command = command
        self.directory = directory
        self.dry = dry
        self.step = step
        self.client = client
        self.md5 = hashlib.md5(str(command).encode("utf-8")).hexdigest()

    # executes the command if it hasn't been executed yet
    # in "dry" mode, prints the command's status, whether it will be executed or not
    # in "step" mode, asks confirmation before running each step
    def handle(self):
        if self.dry:
            print(blue("  todo") if self._todo() else green("  done"), self.command)
        elif not self._todo():
            print(green("skipping"), self.command)
        else:
            if self.step:
                print(blue("next:"), self.command)
                print(blue("(e)xecute,"), green("(s)kip,"), yellow("always ski(p),"), red("(a)bort ?"))

                choice = sys.stdin.readline().strip()
                if choice == "e":
                    print(blue("executing"))
                elif choice == "s":
                    print(green("skipped"))
                    return
                elif choice == "p":  # to always skip a command, we write a history file even if the command hasn't been executed
                    self._write_history_file()
                    print(green("skipped"))
                    return
                else:  # choice "a"
                    print(red("aborting"))
                    exit(0)
            else:
                print(blue("executing"), self.command)

            # failure tolerance: max 4 attempts for each command to succeed
            for retry in reversed(range(4)):
                if self.execute():
                    self._write_history_file()
                    print(green("done"))
                    return
                elif retry:  # on failure, if there are still retries to do, we wait before looping again
                    time.sleep(10)
                    print(blue("retrying"))
                else:
                    print(red("error"))
                    exit(1)

    def execute(self):
        raise NotImplementedError  # abstract function

    # returns whether or not the command has already been executed before (i.e. has a history file)
    def _todo(self):
        return not os.path.isfile(get_full_path(self.md5, self.directory))

    # creates a history file to log the command's execution
    def _write_history_file(self):
        pathlib.Path(get_full_path(self.md5, self.directory)).write_text(str(self.command))


class Command(Task):
    def execute(self):
        # opens a subshell to execute the command, and prints stdout and stderr lines as they come
        return subprocess.Popen(self.command, shell=True, stdout=sys.stdout, stderr=sys.stderr).wait() == 0


class Lookup(Task):
    def execute(self):
        try:
            path = pathlib.Path(self.command.get("path"))
            path.parent.mkdir(parents=True, exist_ok=True)  # ensures the parent directories exist
            path.write_text(self.client.lookup(self.command.get("lookup"), strip=False))
            return True
        except Exception as e:
            print(red(str(e)))
            return False
