import tempfile
from pathlib import Path

import zebr0_script


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
