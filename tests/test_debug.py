import io
from pathlib import Path

import zebr0

import zebr0_script


def test_quit(tmp_path, monkeypatch, capsys):
    def mock_recursive_fetch_script(*_):
        yield "one", tmp_path.joinpath("one")
        yield "two", tmp_path.joinpath("two")

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr("sys.stdin", io.StringIO("q\n"))

    zebr0_script.debug("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'next: "one"\n(e)xecute, (s)kip, or (q)uit?\n'


def test_skip(tmp_path, monkeypatch, capsys):
    def mock_recursive_fetch_script(*_):
        yield "one", tmp_path.joinpath("one")
        yield "two", tmp_path.joinpath("two")

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr("sys.stdin", io.StringIO("s\ns\n"))

    zebr0_script.debug("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'next: "one"\n(e)xecute, (s)kip, or (q)uit?\nnext: "two"\n(e)xecute, (s)kip, or (q)uit?\n'


def test_execute_ok(tmp_path, monkeypatch, capsys):
    report = tmp_path.joinpath("report")

    def mock_recursive_fetch_script(*_):
        yield "test", report

    def mock_execute(command, *_):
        return {"command": command, "stdout": []}

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr(zebr0_script, "execute", mock_execute)
    monkeypatch.setattr("sys.stdin", io.StringIO("e\ny\n"))

    zebr0_script.debug("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'next: "test"\n(e)xecute, (s)kip, or (q)uit?\nwrite report? (y)es or (n)o\n'
    assert report.read_text(encoding=zebr0.ENCODING) == '{\n  "command": "test",\n  "stdout": []\n}'


def test_execute_ko(tmp_path, monkeypatch, capsys):
    report1 = tmp_path.joinpath("report1")
    report2 = tmp_path.joinpath("report2")

    def mock_recursive_fetch_script(*_):
        yield {"key": "yin", "target": "yang"}, report1
        yield "two", report2

    def mock_fetch_to_disk(*_, **__):
        pass

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr(zebr0_script, "fetch_to_disk", mock_fetch_to_disk)
    monkeypatch.setattr("sys.stdin", io.StringIO("e\nq\n"))

    zebr0_script.debug("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'next: {"key": "yin", "target": "yang"}\n(e)xecute, (s)kip, or (q)uit?\nerror: {"key": "yin", "target": "yang"}\nnext: "two"\n(e)xecute, (s)kip, or (q)uit?\n'
    assert not report1.exists()
    assert not report2.exists()
