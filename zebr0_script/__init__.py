import datetime
import hashlib
import os.path
import subprocess
import sys
import time
from pathlib import Path

import yaml

import zebr0


# main function: prints a history of all executed commands
def history(directory, **_):
    def _get_mtime(_file):
        return os.path.getmtime(os.path.join(directory, _file))

    if os.path.isdir(directory):
        for filename in sorted(os.listdir(directory), key=_get_mtime):
            with open(os.path.join(directory, filename)) as file:
                timestamp = _get_mtime(filename)
                strformat = datetime.datetime.fromtimestamp(timestamp).strftime("%c")
                print(filename, strformat, file.read().strip())


# main function: downloads then processes a given script
def run(url, levels, cache, configuration_file, directory, script, **_):
    # ensures that history path exists
    if not os.path.isdir(directory):
        os.makedirs(directory)

    client = zebr0.Client(url, levels, cache, configuration_file)
    for task, history_file in recursive_lookup2(script, directory, client):
        if history_file.is_file():
            print("skipping", task)
        else:
            print("executing", task)

            if isinstance(task, str):
                execute(task, history_file)
            else:
                lookup(task, history_file, client)


def show(url, levels, cache, configuration_file, directory: Path, script, **_):
    client = zebr0.Client(url, levels, cache, configuration_file)
    for task, history_file in recursive_lookup2(script, directory, client):
        print("  todo" if not history_file.is_file() else "  done", task)


def recursive_lookup2(script, directory, client):
    for task in yaml.load(client.get(script), Loader=yaml.BaseLoader):
        if isinstance(task, dict) and task.get("include"):
            yield from recursive_lookup2(task.get("include"), directory, client)
        elif isinstance(task, str) or isinstance(task, dict) and task.get("lookup") and task.get("path"):
            md5 = hashlib.md5(str(task).encode("utf-8")).hexdigest()
            yield task, directory.joinpath(md5)
        else:
            print("unknown command, ignored:", task)


def lookup(task, history_file, client):
    path = Path(task.get("path"))
    path.parent.mkdir(parents=True, exist_ok=True)  # ensures the parent directories exist
    path.write_text(client.get(task.get("lookup"), strip=False))
    history_file.write_text(str(task))
    print("done")


def execute_command(task):
    return subprocess.Popen(task, shell=True, stdout=sys.stdout, stderr=sys.stderr).wait() == 0


def execute(task, history_file):
    # failure tolerance: max 4 attempts for each command to succeed
    for retry in reversed(range(4)):
        if execute_command(task):
            history_file.write_text(task)
            print("done")
            break
        elif retry:  # on failure, if there are still retries to do, we wait before looping again
            time.sleep(10)
            print("retrying")
        else:
            print("error")
            break
