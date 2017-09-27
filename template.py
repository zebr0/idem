#!/usr/bin/python3 -u

import re
import subprocess
import sys


def execute(match):
    # executes through shell the content of the first (only) group matched by the regex
    process = subprocess.run(match.group(1), shell=True, stdout=subprocess.PIPE)
    # cleans the output then returns it
    return process.stdout.decode('UTF-8').strip()


# entrypoint
if __name__ == '__main__':
    # reads each line from stdin
    for line in sys.stdin:
        # replaces each {{ block }} by the stdout of its execution through shell
        sub = re.sub('{{(.+?)}}', execute, line)
        # then writes the processed line to stdout
        sys.stdout.write(sub)
