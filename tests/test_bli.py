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


def test_show(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        historyfile1 = tmp.joinpath("historyfile1")
        historyfile2 = tmp.joinpath("historyfile2")

        def fake_recursive_lookup2(*_):
            yield "test1", historyfile1
            yield "test2", historyfile2

        monkeypatch.setattr(zebr0_script, "recursive_fetch_script", fake_recursive_lookup2)

        zebr0_script.show("http://localhost:8001", [], 1, Path(""), tmp, "script")
        assert capsys.readouterr().out == "  todo test1\n  todo test2\n"

        historyfile1.touch()

        zebr0_script.show("http://localhost:8001", [], 1, Path(""), tmp, "script")
        assert capsys.readouterr().out == "  done test1\n  todo test2\n"

        historyfile2.touch()

        zebr0_script.show("http://localhost:8001", [], 1, Path(""), tmp, "script")
        assert capsys.readouterr().out == "  done test1\n  done test2\n"


def test_run(monkeypatch, capsys):
    with tempfile.TemporaryDirectory() as tmp:
        historypath = Path(tmp).joinpath("history")
        historyfile1 = historypath.joinpath("historyfile1")
        historyfile2 = historypath.joinpath("historyfile2")

        def fake_recursive_lookup2(*_):
            yield "test", historyfile1
            yield {"key": "yin", "target": "yang"}, historyfile2

        def fake_execute(*_):
            return ["hello", "world"]

        def fake_fetch_to_disk(_, key, target):
            return {"key": key, "target": target}

        monkeypatch.setattr(zebr0_script, "recursive_fetch_script", fake_recursive_lookup2)
        monkeypatch.setattr(zebr0_script, "execute", fake_execute)
        monkeypatch.setattr(zebr0_script, "fetch_to_disk", fake_fetch_to_disk)

        zebr0_script.run("http://localhost:8001", [], 1, Path(""), historypath, "script", 4, 1)
        assert capsys.readouterr().out == "executing test\ndone\nexecuting {'key': 'yin', 'target': 'yang'}\ndone\n"
        assert historyfile1.read_text() == "test"
        assert historyfile2.read_text() == "{'key': 'yin', 'target': 'yang'}"

        zebr0_script.run("http://localhost:8001", [], 1, Path(""), historypath, "script", 4, 1)
        assert capsys.readouterr().out == "skipping test\nskipping {'key': 'yin', 'target': 'yang'}\n"

        # todo: test errors (script must stop)


def test_history(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        historypath = Path(tmp).joinpath("history")
        zebr0_script.history(historypath)
        assert capsys.readouterr().out == ""

        historypath.mkdir()
        historyfile1 = historypath.joinpath("historyfile1")
        historyfile1.write_text("hello")
        hf1mtime = historyfile1.stat().st_mtime
        time.sleep(0.1)
        historyfile2 = historypath.joinpath("historyfile2")
        historyfile2.write_text("no way")
        hf2mtime = historyfile2.stat().st_mtime

        zebr0_script.history(historypath)
        assert capsys.readouterr().out == "historyfile1 " + datetime.datetime.fromtimestamp(hf1mtime).strftime("%c") + " hello\nhistoryfile2 " + datetime.datetime.fromtimestamp(hf2mtime).strftime("%c") + " no way\n"


def test_cli(server, capsys):
    server.data = {"script": ["echo one && sleep 1", "echo two"]}

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        history = Path(tmp).joinpath("history")
        configuration_file = tmp.joinpath("zebr0.conf")
        configuration_file.write_text('{"url": "http://127.0.0.1:8000", "levels": ["lorem", "ipsum"], "cache": 1}')

        zebr0_script.main(["-d", str(history), "history"])
        assert capsys.readouterr().out == ""

        zebr0_script.main(["-f", str(configuration_file), "-d", str(history), "show"])
        assert capsys.readouterr().out == "  todo echo one && sleep 1\n  todo echo two\n"

        zebr0_script.main(["-f", str(configuration_file), "-d", str(history), "run"])
        assert capsys.readouterr().out == "executing echo one && sleep 1\none\ndone\nexecuting echo two\ntwo\ndone\n"

        history_file1_md5 = hashlib.md5(json.dumps("echo one && sleep 1").encode(zebr0.ENCODING)).hexdigest()
        historyfile1 = Path(tmp).joinpath("history").joinpath(history_file1_md5)
        hf1mtime = historyfile1.stat().st_mtime
        history_file2_md5 = hashlib.md5(json.dumps("echo two").encode(zebr0.ENCODING)).hexdigest()
        historyfile2 = Path(tmp).joinpath("history").joinpath(history_file2_md5)
        hf2mtime = historyfile2.stat().st_mtime

        zebr0_script.main(["-d", str(history), "history"])
        assert capsys.readouterr().out == history_file1_md5 + " " + datetime.datetime.fromtimestamp(hf1mtime).strftime("%c") + " echo one && sleep 1\n" + history_file2_md5 + " " + datetime.datetime.fromtimestamp(hf2mtime).strftime("%c") + " echo two\n"

        zebr0_script.main(["-f", str(configuration_file), "-d", str(history), "show"])
        assert capsys.readouterr().out == "  done echo one && sleep 1\n  done echo two\n"

        zebr0_script.main(["-f", str(configuration_file), "-d", str(history), "run"])
        assert capsys.readouterr().out == "skipping echo one && sleep 1\nskipping echo two\n"

# TODO: tests connection ko & tests script or lookup ko
