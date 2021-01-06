from pathlib import Path

import zebr0_script

OK_OUTPUT = """
skipping: "one"
executing: "two"
success!
executing: {"key": "yin", "target": "yang"}
success!
""".lstrip()

OK_REPORT2 = """{
  "command": "two",
  "status": "success",
  "output": [
    "Lorem ipsum dolor sit amet",
    "consectetur adipiscing elit",
    "sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
  ]
}"""

OK_REPORT3 = """{
  "key": "yin",
  "target": "yang",
  "status": "success",
  "output": []
}"""


def test_ok(tmp_path, monkeypatch, capsys):
    reports_path = tmp_path.joinpath("reports")
    report1 = reports_path.joinpath("report1")
    report2 = reports_path.joinpath("report2")
    report3 = reports_path.joinpath("report3")

    def mock_recursive_fetch_script(*_):
        yield "one", zebr0_script.Status.SUCCESS, report1
        yield "two", zebr0_script.Status.FAILURE, report2
        yield {"key": "yin", "target": "yang"}, zebr0_script.Status.PENDING, report3

    def mock_execute(command, *_):
        return {"command": command, "status": zebr0_script.Status.SUCCESS, "output": ["Lorem ipsum dolor sit amet", "consectetur adipiscing elit", "sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."]}

    def mock_fetch_to_disk(_, key, target):
        return {"key": key, "target": target, "status": zebr0_script.Status.SUCCESS, "output": []}

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr(zebr0_script, "execute", mock_execute)
    monkeypatch.setattr(zebr0_script, "fetch_to_disk", mock_fetch_to_disk)

    zebr0_script.run("http://localhost:8001", [], 1, Path(""), reports_path, "script")
    assert capsys.readouterr().out == OK_OUTPUT
    assert not report1.exists()
    assert report2.read_text() == OK_REPORT2
    assert report3.read_text() == OK_REPORT3


KO_OUTPUT = """
executing: "one"
error: [
  "error"
]
""".lstrip()

KO_REPORT1 = """{
  "command": "one",
  "status": "failure",
  "output": [
    "error"
  ]
}"""


def test_ko(tmp_path, monkeypatch, capsys):
    report1 = tmp_path.joinpath("report1")
    report2 = tmp_path.joinpath("report2")

    def mock_recursive_fetch_script(*_):
        yield "one", zebr0_script.Status.PENDING, report1
        yield "two", zebr0_script.Status.PENDING, report2

    def mock_execute(command, *_):
        return {"command": command, "status": zebr0_script.Status.FAILURE, "output": ["error"]}

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr(zebr0_script, "execute", mock_execute)

    zebr0_script.run("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == KO_OUTPUT
    assert report1.read_text() == KO_REPORT1
    assert not report2.exists()
