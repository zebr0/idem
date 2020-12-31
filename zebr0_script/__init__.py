import datetime
import hashlib
import json
import subprocess
import sys
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


def show(url: str, levels: Optional[List[str]], cache: int, configuration_file: Path, reports_path: Path, key: str, **_) -> None:
    """
    Fetches a script from the key-value server and displays its tasks along with their current status, whether they have already been executed or not.

    :param url: (zebr0) URL of the key-value server, defaults to https://hub.zebr0.io
    :param levels: (zebr0) levels of specialization (e.g. ["mattermost", "production"] for a <project>/<environment>/<key> structure), defaults to []
    :param cache: (zebr0) in seconds, the duration of the cache of http responses, defaults to 300 seconds
    :param configuration_file: (zebr0) path to the configuration file, defaults to /etc/zebr0.conf for a system-wide configuration
    :param reports_path: Path to the reports' directory
    :param key: key of the script to look for
    """

    client = zebr0.Client(url, levels, cache, configuration_file)
    for task, report_path in recursive_fetch_script(client, key, reports_path):
        print("todo:" if not report_path.exists() else "done:", json.dumps(task))


def execute(command: str, attempts: int = ATTEMPTS_DEFAULT, pause: float = PAUSE_DEFAULT) -> dict:
    """
    Executes a command with the system's shell.
    Several attempts will be made in case of failure, to cover for e.g. network issues.
    Progress is shown with dots, and standard output will be returned as a list of strings if successful.

    :param command: command to execute
    :param attempts: maximum number of attempts before being actually considered a failure
    :param pause: delay in seconds between two attempts
    :return: if successful, an execution report as a dictionary
    """

    for attempt in reversed(range(attempts)):  # [attempts-1 .. 0]
        sp = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding=zebr0.ENCODING)

        output = []
        for line in sp.stdout:
            print(".", end="")  # progress bar: each line in stdout prints a dot
            output.append(line.rstrip())

        if output:
            print()  # if at least one dot has been printed, we need a new line

        if sp.wait() == 0:  # if successful (i.e. the return code is 0)
            return {"command": command, "output": output}
        elif attempt != 0:
            print(f"failed, {attempt} attempts remaining, will try again in {pause} seconds")
            time.sleep(pause)


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
            target_path.write_text(value, encoding=zebr0.ENCODING)

            return {KEY: key, TARGET: target}
        except OSError as error:
            print(error)


def run(url: str, levels: Optional[List[str]], cache: int, configuration_file: Path, reports_path: Path, key: str, attempts: int = ATTEMPTS_DEFAULT, pause: float = PAUSE_DEFAULT, **_) -> None:
    """
    Fetches a script from the key-value server and executes its tasks in order.
    On each success, a report file is created, which serves as an "idempotence" marker not to run the task again.
    On failure, the whole loop stops.

    :param url: (zebr0) URL of the key-value server, defaults to https://hub.zebr0.io
    :param levels: (zebr0) levels of specialization (e.g. ["mattermost", "production"] for a <project>/<environment>/<key> structure), defaults to []
    :param cache: (zebr0) in seconds, the duration of the cache of http responses, defaults to 300 seconds
    :param configuration_file: (zebr0) path to the configuration file, defaults to /etc/zebr0.conf for a system-wide configuration
    :param reports_path: Path to the reports' directory
    :param key: key of the script to look for
    :param attempts: maximum number of attempts before a task is actually considered a failure
    :param pause: delay in seconds between two attempts
    """

    reports_path.mkdir(parents=True, exist_ok=True)  # make sure the parent directories exist

    client = zebr0.Client(url, levels, cache, configuration_file)
    for task, report_path in recursive_fetch_script(client, key, reports_path):
        task_json = json.dumps(task)

        if report_path.exists():
            print("skipping:", task_json)
        else:
            print("executing:", task_json)

            if isinstance(task, str):
                report = execute(task, attempts, pause)
            else:
                report = fetch_to_disk(client, **task)

            if report:
                print("success:", task_json)
                report_path.write_text(json.dumps(report, indent=2), encoding=zebr0.ENCODING)
            else:
                print("error:", task_json)
                break


def log(reports_path: Path, **_) -> None:
    """
    Prints a chronologically ordered list of the report files and their content.

    :param reports_path: Path to the reports' directory
    """

    def get_mtime(path):
        return path.stat().st_mtime

    if reports_path.exists():
        for file in filter(lambda p: p.is_file(), sorted(reports_path.iterdir(), key=get_mtime)):
            strformat = datetime.datetime.fromtimestamp(get_mtime(file)).strftime("%c")
            print(file.name, strformat, file.read_text(encoding=zebr0.ENCODING).strip())


def debug(url: str, levels: Optional[List[str]], cache: int, configuration_file: Path, reports_path: Path, key: str, **_) -> None:
    """
    Fetches a script from the key-value server and executes its tasks one by one via user interaction.
    Useful for debugging scripts in test environment.

    :param url: (zebr0) URL of the key-value server, defaults to https://hub.zebr0.io
    :param levels: (zebr0) levels of specialization (e.g. ["mattermost", "production"] for a <project>/<environment>/<key> structure), defaults to []
    :param cache: (zebr0) in seconds, the duration of the cache of http responses, defaults to 300 seconds
    :param configuration_file: (zebr0) path to the configuration file, defaults to /etc/zebr0.conf for a system-wide configuration
    :param reports_path: Path to the reports' directory
    :param key: key of the script to look for
    """

    reports_path.mkdir(parents=True, exist_ok=True)  # make sure the parent directories exist

    client = zebr0.Client(url, levels, cache, configuration_file)
    for task, report_path in recursive_fetch_script(client, key, reports_path):
        task_json = json.dumps(task)

        if report_path.exists():
            print("already executed:", task_json)
            print("(s)kip, (e)xecute anyway, or (q)uit?")
        else:
            print("next:", task_json)
            print("(e)xecute, (s)kip, or (q)uit?")

        choice = sys.stdin.readline().strip()
        if choice == "s":
            continue
        elif choice == "e":
            if isinstance(task, str):
                report = execute(task, 1)
            else:
                report = fetch_to_disk(client, **task)

            if report:
                print("write report? (y)es or (n)o")
                choice = sys.stdin.readline().strip()
                if choice == "y":
                    report_path.write_text(json.dumps(report, indent=2), encoding=zebr0.ENCODING)
            else:
                print("error:", task_json)
        else:
            return


def main(args: Optional[List[str]] = None) -> None:
    """
    usage: [-h] [-u <url>] [-l [<level> [<level> ...]]] [-c <duration>] [-f <path>] [-r <path>] {show,run,log,debug} ...

    Minimalist local deployment based on zebr0 key-value system.

    positional arguments:
      {show,run,log,debug}
        show                fetches a script from the key-value server and displays its tasks along with their current status, whether they have already been executed or not
        run                 fetches a script from the key-value server and executes its tasks in order
        log                 prints a chronologically ordered list of the report files and their content
        debug               fetches a script from the key-value server and executes its tasks one by one via user interaction

    optional arguments:
      -h, --help            show this help message and exit
      -u <url>, --url <url>
                            URL of the key-value server, defaults to https://hub.zebr0.io
      -l [<level> [<level> ...]], --levels [<level> [<level> ...]]
                            levels of specialization (e.g. "mattermost production" for a <project>/<environment>/<key> structure), defaults to ""
      -c <duration>, --cache <duration>
                            in seconds, the duration of the cache of http responses, defaults to 300 seconds
      -f <path>, --configuration-file <path>
                            path to the configuration file, defaults to /etc/zebr0.conf for a system-wide configuration
      -r <path>, --reports-path <path>
                            path to the reports' directory
    """

    argparser = zebr0.build_argument_parser(description="Minimalist local deployment based on zebr0 key-value system.")
    argparser.add_argument("-r", "--reports-path", type=Path, default=Path("/var/zebr0/script/reports"), help="path to the reports' directory", metavar="<path>")
    subparsers = argparser.add_subparsers()

    show_parser = subparsers.add_parser("show", description="Fetches a script from the key-value server and displays its tasks along with their current status, whether they have already been executed or not.",
                                        help="fetches a script from the key-value server and displays its tasks along with their current status, whether they have already been executed or not")
    show_parser.add_argument("key", nargs="?", default="script", help='key of the script to look for, defaults to "script"')
    show_parser.set_defaults(command=show)

    run_parser = subparsers.add_parser("run", description="Fetches a script from the key-value server and executes its tasks in order. On each success, a report file is created, which serves as an 'idempotence' marker not to run the task again. On failure, the whole loop stops.",
                                       help="fetches a script from the key-value server and executes its tasks in order")
    run_parser.add_argument("key", nargs="?", default="script", help='key of the script to look for, defaults to "script"')
    run_parser.add_argument("--attempts", type=int, default=ATTEMPTS_DEFAULT, help=f"maximum number of attempts before a task is actually considered a failure, defaults to {ATTEMPTS_DEFAULT}", metavar="<value>")
    run_parser.add_argument("--pause", type=float, default=PAUSE_DEFAULT, help=f"delay in seconds between two attempts, defaults to {PAUSE_DEFAULT}", metavar="<value>")
    run_parser.set_defaults(command=run)

    log_parser = subparsers.add_parser("log", description="Prints a chronologically ordered list of the report files and their content.",
                                       help="prints a chronologically ordered list of the report files and their content")
    log_parser.set_defaults(command=log)

    debug_parser = subparsers.add_parser("debug", description="Fetches a script from the key-value server and executes its tasks one by one via user interaction. Useful for debugging scripts in test environment.",
                                         help="fetches a script from the key-value server and executes its tasks one by one via user interaction")
    debug_parser.add_argument("key", nargs="?", default="script", help='key of the script to look for, defaults to "script"')
    debug_parser.set_defaults(command=debug)

    args = argparser.parse_args(args)
    args.command(**vars(args))
