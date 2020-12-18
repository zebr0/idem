import threading
import time

import zebr0_script


def test_ok():
    assert zebr0_script.shell("echo ok") == (0, ["ok"])


def test_ko():
    assert zebr0_script.shell("echo ko && false") == (1, ["ko"])


def test_stdout(capsys):
    def execute():
        zebr0_script.shell("echo begin && sleep 1 && echo end")

    t = threading.Thread(target=execute)
    t.start()
    time.sleep(0.5)
    assert capsys.readouterr().out == "begin\n"
    t.join()
    assert capsys.readouterr().out == "end\n"


def test_multiline(capsys):
    assert zebr0_script.shell("echo one && echo two && echo three") == (0, ["one", "two", "three"])
    assert capsys.readouterr().out == "one\ntwo\nthree\n"
