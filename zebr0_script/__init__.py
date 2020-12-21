import datetime
import hashlib
import os.path
import subprocess
import time
from pathlib import Path

import yaml
import zebr0

ATTEMPTS_DEFAULT = 4
PAUSE_DEFAULT = 10


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
def run(url, levels, cache, configuration_file, directory, script, attempts, pause, **_):
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
                trace = execute(task, attempts, pause)
                if trace:
                    print("done")
                    history_file.write_text(task)
                else:
                    print("error")
                    break
            else:
                trace = lookup(task, client)
                if trace:
                    print("done")
                    history_file.write_text(trace)
                else:
                    print("error")
                    break


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


def lookup(task, client):
    path = Path(task.get("path"))
    path.parent.mkdir(parents=True, exist_ok=True)  # ensures the parent directories exist
    path.write_text(client.get(task.get("lookup"), strip=False))
    return str(task)


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
    argparser.add_argument("-d", "--directory", type=Path, default=Path("/var/zebr0/history"), help="path to the history files directory (default: /var/zebr0/history)")
    subparsers = argparser.add_subparsers()

    history_parser = subparsers.add_parser("history")
    history_parser.set_defaults(command=history)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("script", nargs="?", default="script", help="script identifier in the repository (default: script)")
    run_parser.add_argument("--attempts", type=int, default=ATTEMPTS_DEFAULT, help="")
    run_parser.add_argument("--pause", type=float, default=PAUSE_DEFAULT, help="")
    run_parser.set_defaults(command=run)

    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("script", nargs="?", default="script", help="script identifier in the repository (default: script)")
    show_parser.set_defaults(command=show)

    args = argparser.parse_args(argv)
    args.command(**vars(args))
