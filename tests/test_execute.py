import threading
import time

import zebr0_script


def test_ok(capsys):
    command = "echo ok"
    assert zebr0_script.execute(command) == {"command": command, "stdout": ["ok"]}
    assert capsys.readouterr().out == "ok\n"


def test_ko(capsys):
    assert zebr0_script.execute("echo ko && false", attempts=3, pause=0.1) is None
    assert capsys.readouterr().out == "ko\nfailed, 2 attempts remaining, will try again in 0.1 seconds\nko\nfailed, 1 attempts remaining, will try again in 0.1 seconds\nko\n"


def test_stdout(capsys):
    def execute():
        zebr0_script.execute("echo begin && sleep 1 && echo end")

    t = threading.Thread(target=execute)
    t.start()
    time.sleep(0.5)
    assert capsys.readouterr().out == "begin\n"
    t.join()
    assert capsys.readouterr().out == "end\n"


def test_multiline(capsys):
    command = "echo one && echo two && echo three"
    assert zebr0_script.execute(command) == {"command": command, "stdout": ["one", "two", "three"]}
    assert capsys.readouterr().out == "one\ntwo\nthree\n"


def test_ko_then_ok(tmp_path, capsys):
    command = f"[ -f {tmp_path}/file ] || ! touch {tmp_path}/file"
    assert zebr0_script.execute(command, pause=0.1) == {"command": command, "stdout": []}
    assert capsys.readouterr().out == "failed, 3 attempts remaining, will try again in 0.1 seconds\n"
