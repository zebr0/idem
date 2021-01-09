import datetime
import enum
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
COMMAND = "command"
STATUS = "status"
OUTPUT = "output"


class Status(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILURE = "failure"


def recursive_fetch_script(client: zebr0.Client, key: str, reports_path: Path) -> Iterator[Tuple[Any, Status, Path]]:
    """
    Fetches a script from the key-value server and yields its tasks, their Status and report Path.
    Included scripts are fetched recursively.
    Malformed tasks are ignored.

    :param client: zebr0 Client to the key-value server
    :param key: the script's key
    :param reports_path: Path to the reports' directory
    :return: the script's tasks, their Status and report Path
    """

    value = client.get(key)
    if not value:
        print(f"key '{key}' not found on server {client.url}")
        return

    tasks = yaml.load(value, Loader=yaml.BaseLoader)
    if not isinstance(tasks, list):
        print(f"key '{key}' on server {client.url} is not a proper yaml or json list")
        return

    for task in tasks:
        if isinstance(task, dict) and task.keys() == {INCLUDE}:
            yield from recursive_fetch_script(client, task.get(INCLUDE), reports_path)
        elif isinstance(task, str) or isinstance(task, dict) and task.keys() == {KEY, TARGET}:
            md5 = hashlib.md5(json.dumps(task).encode(zebr0.ENCODING)).hexdigest()
            report_path = reports_path.joinpath(md5)
            status = Status.PENDING if not report_path.exists() else json.loads(report_path.read_text(encoding=zebr0.ENCODING)).get(STATUS)

            yield task, status, report_path
        else:
            print("malformed task, ignored:", json.dumps(task))


def show(url: str, levels: Optional[List[str]], cache: int, configuration_file: Path, reports_path: Path, key: str, **_) -> None:
    """
    Fetches a script from the key-value server and displays its tasks along with their current status.

    :param url: (zebr0) URL of the key-value server, defaults to https://hub.zebr0.io
    :param levels: (zebr0) levels of specialization (e.g. ["mattermost", "production"] for a <project>/<environment>/<key> structure), defaults to []
    :param cache: (zebr0) in seconds, the duration of the cache of http responses, defaults to 300 seconds
    :param configuration_file: (zebr0) path to the configuration file, defaults to /etc/zebr0.conf for a system-wide configuration
    :param reports_path: Path to the reports' directory
    :param key: the script's key
    """

    client = zebr0.Client(url, levels, cache, configuration_file)
    for task, status, _ in recursive_fetch_script(client, key, reports_path):
        print(f"{status}: {json.dumps(task)}")


def execute(command: str, attempts: int = ATTEMPTS_DEFAULT, pause: float = PAUSE_DEFAULT) -> dict:
    """
    Executes a command with the system's shell.
    Several attempts will be made in case of failure, to cover for temporary mishaps such as network issues.
    Progress is shown with dots, and standard output will be returned as a list of strings in an execution report.

    :param command: command to execute
    :param attempts: maximum number of attempts before reporting a failure
    :param pause: delay in seconds between two attempts
    :return: an execution report
    """

    while True:
        sp = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding=zebr0.ENCODING)
        attempts = attempts - 1

        output = []
        for line in sp.stdout:
            print(".", end="")  # progress bar: each line in stdout prints a dot
            output.append(line.rstrip())
        if output:
            print()  # if at least one dot has been printed, we need a new line at the end

        if sp.wait() == 0:  # if successful (i.e. the return code is 0)
            status = Status.SUCCESS
            break
        elif attempts > 0:
            print(f"error, {attempts} attempts remaining, will try again in {pause} seconds")
            time.sleep(pause)
        else:
            status = Status.FAILURE
            break

    return {COMMAND: command, STATUS: status, OUTPUT: output}  # last known output


def fetch_to_disk(client: zebr0.Client, key: str, target: str) -> dict:
    """
    Fetches a key from the key-value server and writes its value into a target file.
    Errors will be returned as a list of strings in an execution report.

    :param client: zebr0 Client to the key-value server
    :param key: key to look for
    :param target: path to the target file
    :return: an execution report
    """

    value = client.get(key, strip=False)
    if not value:
        status = Status.FAILURE
        output = [f"key '{key}' not found on server {client.url}"]
    else:
        try:
            target_path = Path(target)
            target_path.parent.mkdir(parents=True, exist_ok=True)  # make sure the parent directory exists
            target_path.write_text(value, encoding=zebr0.ENCODING)

            status = Status.SUCCESS
            output = []
        except OSError as error:
            status = Status.FAILURE
            output = str(error).splitlines()

    return {KEY: key, TARGET: target, STATUS: status, OUTPUT: output}


def run(url: str, levels: Optional[List[str]], cache: int, configuration_file: Path, reports_path: Path, key: str, attempts: int = ATTEMPTS_DEFAULT, pause: float = PAUSE_DEFAULT, **_) -> None:
    """
    Fetches a script from the key-value server and executes its tasks.
    Execution reports are written after each task.
    On failure, the output is displayed and the loop stops.
    Should you run the script again, successful tasks will be skipped.

    :param url: (zebr0) URL of the key-value server, defaults to https://hub.zebr0.io
    :param levels: (zebr0) levels of specialization (e.g. ["mattermost", "production"] for a <project>/<environment>/<key> structure), defaults to []
    :param cache: (zebr0) in seconds, the duration of the cache of http responses, defaults to 300 seconds
    :param configuration_file: (zebr0) path to the configuration file, defaults to /etc/zebr0.conf for a system-wide configuration
    :param reports_path: Path to the reports' directory
    :param key: the script's key
    :param attempts: maximum number of attempts before reporting a failure
    :param pause: delay in seconds between two attempts
    """

    reports_path.mkdir(parents=True, exist_ok=True)  # make sure the parent directory exists

    client = zebr0.Client(url, levels, cache, configuration_file)
    for task, status, report_path in recursive_fetch_script(client, key, reports_path):
        if status == Status.SUCCESS:
            print("skipping:", json.dumps(task))
            continue

        print("executing:", json.dumps(task))
        report = execute(task, attempts, pause) if isinstance(task, str) else fetch_to_disk(client, **task)
        report_path.write_text(json.dumps(report, indent=2), encoding=zebr0.ENCODING)

        if report.get(STATUS) == Status.SUCCESS:
            print("success!")
            continue

        print("error:", json.dumps(report.get(OUTPUT), indent=2))
        break


def log(reports_path: Path, **_) -> None:
    """
    Displays a time-ordered list of the report files and their content (minus the output).

    :param reports_path: Path to the reports' directory
    """

    if not reports_path.exists():
        return

    def get_mtime(path):
        return path.stat().st_mtime

    for file in filter(lambda p: p.is_file(), sorted(reports_path.iterdir(), key=get_mtime)):
        mtime = datetime.datetime.fromtimestamp(get_mtime(file)).strftime("%c")

        content = json.loads(file.read_text(encoding=zebr0.ENCODING))
        content.pop(OUTPUT)

        print(file.name, mtime, json.dumps(content))


def debug(url: str, levels: Optional[List[str]], cache: int, configuration_file: Path, reports_path: Path, key: str, **_) -> None:
    """
    Fetches a script from the key-value server and executes its tasks through user interaction.
    Useful for debugging scripts in a test environment.

    :param url: (zebr0) URL of the key-value server, defaults to https://hub.zebr0.io
    :param levels: (zebr0) levels of specialization (e.g. ["mattermost", "production"] for a <project>/<environment>/<key> structure), defaults to []
    :param cache: (zebr0) in seconds, the duration of the cache of http responses, defaults to 300 seconds
    :param configuration_file: (zebr0) path to the configuration file, defaults to /etc/zebr0.conf for a system-wide configuration
    :param reports_path: Path to the reports' directory
    :param key: the script's key
    """

    reports_path.mkdir(parents=True, exist_ok=True)  # make sure the parent directory exists

    client = zebr0.Client(url, levels, cache, configuration_file)
    for task, status, report_path in recursive_fetch_script(client, key, reports_path):
        if status == Status.SUCCESS:
            print("already executed:", json.dumps(task))
            print("(s)kip, (e)xecute anyway, or (q)uit?")
        else:
            print("next:", json.dumps(task))
            print("(e)xecute, (s)kip, or (q)uit?")

        choice = sys.stdin.readline().strip()
        if choice == "e":
            report = execute(task, 1) if isinstance(task, str) else fetch_to_disk(client, **task)
            print("success!" if report.get(STATUS) == Status.SUCCESS else f"error: {json.dumps(report.get(OUTPUT), indent=2)}")

            print("write report? (y)es or (n)o")
            choice = sys.stdin.readline().strip()
            if choice == "y":
                report_path.write_text(json.dumps(report, indent=2), encoding=zebr0.ENCODING)
        elif not choice == "s":
            break


def main(args: Optional[List[str]] = None) -> None:
    """
    usage: [-h] [-u <url>] [-l [<level> [<level> ...]]] [-c <duration>] [-f <path>] [-r <path>] {show,run,log,debug} ...

    Minimalist local deployment based on zebr0 key-value system.

    positional arguments:
      {show,run,log,debug}
        show                fetches a script from the key-value server and displays its tasks along with their current status
        run                 fetches a script from the key-value server and executes its tasks
        log                 displays a time-ordered list of the report files and their content (minus the output)
        debug               fetches a script from the key-value server and executes its tasks through user interaction

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
                            path to the reports' directory, defaults to /var/zebr0/script/reports
    """

    argparser = zebr0.build_argument_parser(description="Minimalist local deployment based on zebr0 key-value system.")
    argparser.add_argument("-r", "--reports-path", type=Path, default=Path("/var/zebr0/script/reports"), help="path to the reports' directory, defaults to /var/zebr0/script/reports", metavar="<path>")
    subparsers = argparser.add_subparsers()

    show_parser = subparsers.add_parser("show", description="Fetches a script from the key-value server and displays its tasks along with their current status.",
                                        help="fetches a script from the key-value server and displays its tasks along with their current status")
    show_parser.add_argument("key", nargs="?", default="script", help="the script's key, defaults to 'script'")
    show_parser.set_defaults(command=show)

    run_parser = subparsers.add_parser("run", description="Fetches a script from the key-value server and executes its tasks. Execution reports are written after each task. On failure, the output is displayed and the loop stops. Should you run the script again, successful tasks will be skipped.",
                                       help="fetches a script from the key-value server and executes its tasks")
    run_parser.add_argument("key", nargs="?", default="script", help="the script's key, defaults to 'script'")
    run_parser.add_argument("--attempts", type=int, default=ATTEMPTS_DEFAULT, help=f"maximum number of attempts before reporting a failure, defaults to {ATTEMPTS_DEFAULT}", metavar="<value>")
    run_parser.add_argument("--pause", type=float, default=PAUSE_DEFAULT, help=f"delay in seconds between two attempts, defaults to {PAUSE_DEFAULT}", metavar="<value>")
    run_parser.set_defaults(command=run)

    log_parser = subparsers.add_parser("log", description="Displays a time-ordered list of the report files and their content (minus the output).",
                                       help="displays a time-ordered list of the report files and their content (minus the output)")
    log_parser.set_defaults(command=log)

    debug_parser = subparsers.add_parser("debug", description="Fetches a script from the key-value server and executes its tasks through user interaction. Useful for debugging scripts in a test environment.",
                                         help="fetches a script from the key-value server and executes its tasks through user interaction")
    debug_parser.add_argument("key", nargs="?", default="script", help="the script's key, defaults to 'script'")
    debug_parser.set_defaults(command=debug)

    args = argparser.parse_args(args)
    args.command(**vars(args))
