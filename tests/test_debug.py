import io
from pathlib import Path

import zebr0

import zebr0_script


def test_quit(tmp_path, monkeypatch, capsys):
    def mock_recursive_fetch_script(*_):
        yield "one", zebr0_script.Status.PENDING, tmp_path.joinpath("one")
        yield "two", zebr0_script.Status.PENDING, tmp_path.joinpath("two")

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr("sys.stdin", io.StringIO("q\n"))

    zebr0_script.debug("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'next: "one"\n(e)xecute, (s)kip, or (q)uit?\n'


def test_skip(tmp_path, monkeypatch, capsys):
    def mock_recursive_fetch_script(*_):
        yield "one", zebr0_script.Status.PENDING, tmp_path.joinpath("one")
        yield "two", zebr0_script.Status.PENDING, tmp_path.joinpath("two")

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr("sys.stdin", io.StringIO("s\ns\n"))

    zebr0_script.debug("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'next: "one"\n(e)xecute, (s)kip, or (q)uit?\nnext: "two"\n(e)xecute, (s)kip, or (q)uit?\n'


def test_execute_ok(tmp_path, monkeypatch, capsys):
    report = tmp_path.joinpath("report")

    def mock_recursive_fetch_script(*_):
        yield "test", zebr0_script.Status.PENDING, report

    def mock_execute(command, *_):
        return {"command": command, "status": zebr0_script.Status.SUCCESS, "output": []}

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr(zebr0_script, "execute", mock_execute)
    monkeypatch.setattr("sys.stdin", io.StringIO("e\ny\n"))

    zebr0_script.debug("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'next: "test"\n(e)xecute, (s)kip, or (q)uit?\nsuccess: "test"\nwrite report? (y)es or (n)o\n'
    assert report.read_text(encoding=zebr0.ENCODING) == '{\n  "command": "test",\n  "status": "success",\n  "output": []\n}'


def test_execute_ko(tmp_path, monkeypatch, capsys):
    report1 = tmp_path.joinpath("report1")
    report2 = tmp_path.joinpath("report2")

    def mock_recursive_fetch_script(*_):
        yield {"key": "yin", "target": "yang"}, zebr0_script.Status.PENDING, report1
        yield "two", zebr0_script.Status.PENDING, report2

    def mock_fetch_to_disk(_, key, target):
        return {"key": key, "target": target, "status": zebr0_script.Status.FAILURE, "output": ["error"]}

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr(zebr0_script, "fetch_to_disk", mock_fetch_to_disk)
    monkeypatch.setattr("sys.stdin", io.StringIO("e\ny\nq\n"))

    zebr0_script.debug("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'next: {"key": "yin", "target": "yang"}\n(e)xecute, (s)kip, or (q)uit?\nerror\nerror: {"key": "yin", "target": "yang"}\nwrite report? (y)es or (n)o\nnext: "two"\n(e)xecute, (s)kip, or (q)uit?\n'
    assert report1.exists()
    assert not report2.exists()


def test_already_executed(tmp_path, monkeypatch, capsys):
    def mock_recursive_fetch_script(*_):
        yield {"key": "yin", "target": "yang"}, zebr0_script.Status.SUCCESS, tmp_path.joinpath("report")

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr("sys.stdin", io.StringIO("s\n"))

    zebr0_script.debug("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'already executed: {"key": "yin", "target": "yang"}\n(s)kip, (e)xecute anyway, or (q)uit?\n'
