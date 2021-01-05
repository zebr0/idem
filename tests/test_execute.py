import threading
import time

import zebr0_script


def test_ok(capsys):
    command = "echo one && echo two"
    assert zebr0_script.execute(command) == {"command": command, "status": zebr0_script.Status.SUCCESS, "output": ["one", "two"]}
    assert capsys.readouterr().out == "..\n"


def test_ko(capsys):
    command = "echo ko && false"
    assert zebr0_script.execute(command, attempts=3, pause=0.1) == {"command": command, "status": zebr0_script.Status.FAILURE, "output": ["ko"]}
    assert capsys.readouterr().out == ".\nerror, 2 attempts remaining, will try again in 0.1 seconds\n.\nerror, 1 attempts remaining, will try again in 0.1 seconds\n.\n"


def test_ko_then_ok(tmp_path, capsys):
    command = f"[ -f {tmp_path}/file ] || ! touch {tmp_path}/file"
    assert zebr0_script.execute(command, pause=0.1) == {"command": command, "status": zebr0_script.Status.SUCCESS, "output": []}
    assert capsys.readouterr().out == "error, 3 attempts remaining, will try again in 0.1 seconds\n"


def test_wrong_attempts(capsys):
    command = "echo ko && false"
    assert zebr0_script.execute(command, attempts=0) == {"command": command, "status": zebr0_script.Status.FAILURE, "output": ["ko"]}
    assert capsys.readouterr().out == ".\n"


def test_progress_bar(capsys):
    def execute():
        zebr0_script.execute("echo one && sleep 1 && echo two")

    thread = threading.Thread(target=execute)
    thread.start()
    time.sleep(0.5)
    assert capsys.readouterr().out == "."
    thread.join()
    assert capsys.readouterr().out == ".\n"
