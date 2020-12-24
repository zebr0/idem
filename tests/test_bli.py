import datetime
import hashlib
import json
import tempfile
import time
from pathlib import Path

import pytest
import zebr0

import zebr0_script


@pytest.fixture(scope="module")
def server():
    with zebr0.TestServer() as server:
        yield server


def test_history(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        historypath = Path(tmp).joinpath("history")
        zebr0_script.history(historypath)
        assert capsys.readouterr().out == ""

        historypath.mkdir()
        historyfile1 = historypath.joinpath("historyfile1")
        historyfile1.write_text('{"hello": "world"}')
        hf1mtime = historyfile1.stat().st_mtime
        time.sleep(0.1)
        historyfile2 = historypath.joinpath("historyfile2")
        historyfile2.write_text('{"no": "way"}')
        hf2mtime = historyfile2.stat().st_mtime

        zebr0_script.history(historypath)
        assert capsys.readouterr().out == "historyfile1 " + datetime.datetime.fromtimestamp(hf1mtime).strftime("%c") + ' {"hello": "world"}\nhistoryfile2 ' + datetime.datetime.fromtimestamp(hf2mtime).strftime("%c") + ' {"no": "way"}\n'


def test_cli(server, capsys):
    server.data = {"script": ["echo one && sleep 1", "echo two"]}

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        history = Path(tmp).joinpath("history")
        configuration_file = tmp.joinpath("zebr0.conf")
        configuration_file.write_text('{"url": "http://127.0.0.1:8000", "levels": ["lorem", "ipsum"], "cache": 1}')

        zebr0_script.main(["-r", str(history), "history"])
        assert capsys.readouterr().out == ""

        zebr0_script.main(["-f", str(configuration_file), "-r", str(history), "show"])
        assert capsys.readouterr().out == 'todo: "echo one && sleep 1"\ntodo: "echo two"\n'

        zebr0_script.main(["-f", str(configuration_file), "-r", str(history), "run"])
        assert capsys.readouterr().out == 'executing: "echo one && sleep 1"\none\nsuccess: "echo one && sleep 1"\nexecuting: "echo two"\ntwo\nsuccess: "echo two"\n'

        history_file1_md5 = hashlib.md5(json.dumps("echo one && sleep 1").encode(zebr0.ENCODING)).hexdigest()
        historyfile1 = Path(tmp).joinpath("history").joinpath(history_file1_md5)
        hf1mtime = historyfile1.stat().st_mtime
        history_file2_md5 = hashlib.md5(json.dumps("echo two").encode(zebr0.ENCODING)).hexdigest()
        historyfile2 = Path(tmp).joinpath("history").joinpath(history_file2_md5)
        hf2mtime = historyfile2.stat().st_mtime

        zebr0_script.main(["-r", str(history), "history"])
        assert capsys.readouterr().out == history_file1_md5 + " " + datetime.datetime.fromtimestamp(hf1mtime).strftime("%c") + ' {"command": "echo one && sleep 1", "stdout": ["one"]}\n' + history_file2_md5 + " " + datetime.datetime.fromtimestamp(hf2mtime).strftime(
            "%c") + ' {"command": "echo two", "stdout": ["two"]}\n'

        zebr0_script.main(["-f", str(configuration_file), "-r", str(history), "show"])
        assert capsys.readouterr().out == 'done: "echo one && sleep 1"\ndone: "echo two"\n'

        zebr0_script.main(["-f", str(configuration_file), "-r", str(history), "run"])
        assert capsys.readouterr().out == 'skipping: "echo one && sleep 1"\nskipping: "echo two"\n'

# TODO: tests connection ko & tests script or lookup ko
