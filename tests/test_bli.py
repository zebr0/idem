import tempfile
from pathlib import Path

import pytest

import zebr0
import zebr0_script


@pytest.fixture(scope="module")
def server():
    with zebr0.TestServer() as server:
        yield server


def test_execute_command():
    with tempfile.TemporaryDirectory() as tmp:
        assert zebr0_script.execute_command("touch {}/test".format(tmp))
        assert Path(tmp).joinpath("test").is_file()
        assert not zebr0_script.execute_command("false")
        # with popen used like that, it's impossible to test stdout


def test_execute(monkeypatch, capsys):
    def fake_execute_command(task):
        print("ok")
        return True

    monkeypatch.setattr(zebr0_script, "execute_command", fake_execute_command)

    with tempfile.TemporaryDirectory() as tmp:
        zebr0_script.execute("dummy", Path(tmp).joinpath("test"))
        assert capsys.readouterr().out == "ok\ndone\n"


def test_execute_ko(monkeypatch, capsys):
    def fake_execute_command(task):
        print("ko")
        return False

    monkeypatch.setattr(zebr0_script, "execute_command", fake_execute_command)

    with tempfile.TemporaryDirectory() as tmp:
        zebr0_script.execute("dummy", Path(tmp).joinpath("test"), 5, 0.1)
        assert capsys.readouterr().out == "ko\nretrying\nko\nretrying\nko\nretrying\nko\nretrying\nko\nerror\n"


def test_execute_ko_then_ok(monkeypatch, capsys):
    trick = {}

    def fake_execute_command(task):
        trick["count"] = trick.get("count", 0) + 1
        return trick.get("count") == 3

    monkeypatch.setattr(zebr0_script, "execute_command", fake_execute_command)

    with tempfile.TemporaryDirectory() as tmp:
        zebr0_script.execute("dummy", Path(tmp).joinpath("test"), 3, 0.1)
        assert capsys.readouterr().out == "retrying\nretrying\ndone\n"


def test_lookup(server, capsys):
    server.data = {"data": "dummy\n"}

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        client = zebr0.Client("http://localhost:8000", configuration_file=Path(""))

        testfile = tmp.joinpath("many/directories/test")
        historyfile = tmp.joinpath("history")
        sdfsdf = {"lookup": "data", "path": testfile}

        zebr0_script.lookup(sdfsdf, historyfile, client)

        assert testfile.read_text() == "dummy\n"
        assert historyfile.read_text() == str(sdfsdf)
        assert capsys.readouterr().out == "done\n"
