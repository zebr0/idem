import io
from pathlib import Path

import zebr0

import zebr0_script

SKIP_OUTPUT = """
already executed: "one"
(s)kip, (e)xecute anyway, or (q)uit?
next: "two"
(e)xecute, (s)kip, or (q)uit?
""".lstrip()


def test_skip(tmp_path, monkeypatch, capsys):
    reports_path = tmp_path.joinpath("reports")
    report1 = reports_path.joinpath("report1")
    report2 = reports_path.joinpath("report2")

    def mock_recursive_fetch_script(*_):
        yield "one", zebr0_script.Status.SUCCESS, report1
        yield "two", zebr0_script.Status.PENDING, report2

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr("sys.stdin", io.StringIO("s\ns\n"))

    zebr0_script.debug("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == SKIP_OUTPUT
    assert not report1.exists()
    assert not report2.exists()


QUIT_OUTPUT = """
next: {"key": "yin", "target": "yang"}
(e)xecute, (s)kip, or (q)uit?
""".lstrip()


def test_quit(tmp_path, monkeypatch, capsys):
    report1 = tmp_path.joinpath("report1")
    report2 = tmp_path.joinpath("report2")

    def mock_recursive_fetch_script(*_):
        yield {"key": "yin", "target": "yang"}, zebr0_script.Status.FAILURE, report1
        yield {"key": "ping", "target": "pong"}, zebr0_script.Status.PENDING, report2

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr("sys.stdin", io.StringIO("q\n"))

    zebr0_script.debug("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == QUIT_OUTPUT
    assert not report1.exists()
    assert not report2.exists()


OK_OUTPUT = """
next: "test"
(e)xecute, (s)kip, or (q)uit?
success!
write report? (y)es or (n)o
""".lstrip()

OK_REPORT = """{
  "command": "test",
  "status": "success",
  "output": [
    "Lorem ipsum dolor sit amet",
    "consectetur adipiscing elit",
    "sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
  ]
}"""


def test_ok(tmp_path, monkeypatch, capsys):
    report = tmp_path.joinpath("report")

    def mock_recursive_fetch_script(*_):
        yield "test", zebr0_script.Status.PENDING, report

    def mock_execute(command, *_):
        return {"command": command, "status": zebr0_script.Status.SUCCESS, "output": ["Lorem ipsum dolor sit amet", "consectetur adipiscing elit", "sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."]}

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr(zebr0_script, "execute", mock_execute)
    monkeypatch.setattr("sys.stdin", io.StringIO("e\ny\n"))

    zebr0_script.debug("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == OK_OUTPUT
    assert report.read_text(encoding=zebr0.ENCODING) == OK_REPORT


KO_OUTPUT = """
next: {"key": "yin", "target": "yang"}
(e)xecute, (s)kip, or (q)uit?
error: [
  "error"
]
write report? (y)es or (n)o
""".lstrip()


def test_ko_without_report(tmp_path, monkeypatch, capsys):
    report = tmp_path.joinpath("report")

    def mock_recursive_fetch_script(*_):
        yield {"key": "yin", "target": "yang"}, zebr0_script.Status.PENDING, report

    def mock_fetch_to_disk(_, key, target):
        return {"key": key, "target": target, "status": zebr0_script.Status.FAILURE, "output": ["error"]}

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr(zebr0_script, "fetch_to_disk", mock_fetch_to_disk)
    monkeypatch.setattr("sys.stdin", io.StringIO("e\nn\n"))

    zebr0_script.debug("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == KO_OUTPUT
    assert not report.exists()
