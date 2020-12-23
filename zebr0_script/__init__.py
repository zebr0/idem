import datetime
import hashlib
import json
import os.path
import subprocess
import time
from pathlib import Path
from typing import Tuple, Iterator, Any, Optional, List

import yaml
import zebr0

ATTEMPTS_DEFAULT = 4
PAUSE_DEFAULT = 10

INCLUDE = "include"
KEY = "key"
TARGET = "target"


# main function: prints a history of all executed commands
def history(reports_path, **_):
    def _get_mtime(_file):
        return os.path.getmtime(os.path.join(reports_path, _file))

    if os.path.isdir(reports_path):
        for filename in sorted(os.listdir(reports_path), key=_get_mtime):
            with open(os.path.join(reports_path, filename)) as file:
                timestamp = _get_mtime(filename)
                strformat = datetime.datetime.fromtimestamp(timestamp).strftime("%c")
                print(filename, strformat, file.read().strip())


# main function: downloads then processes a given script
def run(url, levels, cache, configuration_file, reports_path, script, attempts, pause, **_):
    # ensures that history path exists
    if not os.path.isdir(reports_path):
        os.makedirs(reports_path)

    client = zebr0.Client(url, levels, cache, configuration_file)
    for task, history_file in recursive_fetch_script(client, script, reports_path):
        if history_file.is_file():
            print("skipping", task)
        else:
            print("executing", task)

            if isinstance(task, str):
                trace = execute(task, attempts, pause)
                if trace:
                    print("done")
                    history_file.write_text(task)
                else:
                    print("error")
                    break
            else:
                trace = fetch_to_disk(client, **task)
                if trace:
                    print("done")
                    history_file.write_text(str(trace))
                else:
                    print("error")
                    break


def show(url: str, levels: Optional[List[str]], cache: int, configuration_file: Path, reports_path: Path, key: str, **_) -> None:
    """
    Fetches a script from the key-value server and displays its tasks along with their current status, whether they have already been executed or not.

    :param url: URL of the key-value server, defaults to https://hub.zebr0.io
    :param levels: levels of specialization (e.g. ["mattermost", "production"] for a <project>/<environment>/<key> structure), defaults to []
    :param cache: in seconds, the duration of the cache of http responses, defaults to 300 seconds
    :param configuration_file: path to the configuration file, defaults to /etc/zebr0.conf for a system-wide configuration
    :param reports_path: Path to the reports' directory
    :param key: key of the script to look for
    """

    client = zebr0.Client(url, levels, cache, configuration_file)
    for task, report_path in recursive_fetch_script(client, key, reports_path):
        print("todo:" if not report_path.exists() else "done:", json.dumps(task))


def recursive_fetch_script(client: zebr0.Client, key: str, reports_path: Path) -> Iterator[Tuple[Any, Path]]:
    """
    Fetches a script from the key-value server, validates the tasks' structure and fetches the "include" tasks recursively.

    Beware that malformed tasks are ignored.
    Also, "key not found" and "key is not a proper yaml or json list" errors are non-blocking in "include" tasks.

    :param client: zebr0 Client instance to the key-value server
    :param key: key of the script to look for
    :param reports_path: Path to the reports' directory
    :return: the script's valid tasks and the corresponding report Paths
    """

    value = client.get(key)
    if not value:
        print(f"key '{key}' not found on server {client.url}")
    else:
        tasks = yaml.load(value, Loader=yaml.BaseLoader)
        if not isinstance(tasks, list):
            print(f"key '{key}' on server {client.url} is not a proper yaml or json list")
        else:
            for task in tasks:
                if isinstance(task, dict) and task.keys() == {INCLUDE}:
                    yield from recursive_fetch_script(client, task.get(INCLUDE), reports_path)
                elif isinstance(task, str) or isinstance(task, dict) and task.keys() == {KEY, TARGET}:
                    md5 = hashlib.md5(json.dumps(task).encode(zebr0.ENCODING)).hexdigest()
                    yield task, reports_path.joinpath(md5)
                else:
                    print("malformed task, ignored:", json.dumps(task))


def fetch_to_disk(client: zebr0.Client, key: str, target: str) -> dict:
    """
    Fetches a key from the key-value server and writes its value into a target file.

    :param client: zebr0 Client instance to the key-value server
    :param key: key to look for
    :param target: path to the target file
    :return: if successful, an execution report as a dictionary
    """

    value = client.get(key, strip=False)
    if not value:
        print(f"key '{key}' not found on server {client.url}")
    else:
        try:
            target_path = Path(target)
            target_path.parent.mkdir(parents=True, exist_ok=True)  # make sure the parent directories exist
            target_path.write_text(value)

            return {KEY: key, TARGET: target}
        except OSError as error:
            print(error)


def execute(command: str, attempts: int = ATTEMPTS_DEFAULT, pause: float = PAUSE_DEFAULT) -> dict:
    """
    Executes a command with the system's shell.
    Several attempts will be made in case of failure, to cover for e.g. network issues.
    Standard output will be shown and returned as a list of strings if successful.
    Beware that dynamic output like the use of carriage return in progress bars won't be rendered properly.

    :param command: command to execute
    :param attempts: maximum number of attempts before being actually considered a failure
    :param pause: delay in seconds between two attempts
    :return: if successful, an execution report as a dictionary
    """

    for attempt in reversed(range(attempts)):  # [attempts-1 .. 0]
        sp = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, universal_newlines=True, encoding=zebr0.ENCODING)

        stdout = []
        for line in sp.stdout:
            line = line.strip()
            print(line)
            stdout.append(line)

        if sp.wait() == 0:  # if successful (i.e. the return code is 0)
            return {"command": command, "stdout": stdout}
        elif attempt != 0:
            print(f"failed, {attempt} attempts remaining, will try again in {pause} seconds")
            time.sleep(pause)


def main(argv=None):
    argparser = zebr0.build_argument_parser(description="Minimalist local provisioning.")
    argparser.add_argument("-r", "--reports-path", type=Path, default=Path("/var/zebr0/script/reports"), help="")
    subparsers = argparser.add_subparsers()

    history_parser = subparsers.add_parser("history")
    history_parser.set_defaults(command=history)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("script", nargs="?", default="script", help="script identifier in the repository (default: script)")
    run_parser.add_argument("--attempts", type=int, default=ATTEMPTS_DEFAULT, help="")
    run_parser.add_argument("--pause", type=float, default=PAUSE_DEFAULT, help="")
    run_parser.set_defaults(command=run)

    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("key", nargs="?", default="script", help="script identifier in the repository (default: script)")
    show_parser.set_defaults(command=show)

    args = argparser.parse_args(argv)
    args.command(**vars(args))
