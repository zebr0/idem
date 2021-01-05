from pathlib import Path

import zebr0_script

REPORT1_CONTENT = """{
  "command": "test",
  "status": "success",
  "output": [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
  ]
}"""


def test_ok(tmp_path, monkeypatch, capsys):
    reports_path = tmp_path.joinpath("reports")
    report1 = reports_path.joinpath("report1")
    report2 = reports_path.joinpath("report2")

    def mock_recursive_fetch_script(*_):
        yield "test", zebr0_script.Status.PENDING, report1
        yield {"key": "yin", "target": "yang"}, zebr0_script.Status.PENDING, report2

    def mock_execute(command, *_):
        return {"command": command, "status": zebr0_script.Status.SUCCESS, "output": ["Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
                                                                                      "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
                                                                                      "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
                                                                                      "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."]}

    def mock_fetch_to_disk(_, key, target):
        return {"key": key, "target": target, "status": zebr0_script.Status.SUCCESS, "output": []}

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr(zebr0_script, "execute", mock_execute)
    monkeypatch.setattr(zebr0_script, "fetch_to_disk", mock_fetch_to_disk)

    zebr0_script.run("http://localhost:8001", [], 1, Path(""), reports_path, "script")
    assert capsys.readouterr().out == 'executing: "test"\nsuccess: "test"\nexecuting: {"key": "yin", "target": "yang"}\nsuccess: {"key": "yin", "target": "yang"}\n'
    assert report1.read_text() == REPORT1_CONTENT
    assert report2.read_text() == '{\n  "key": "yin",\n  "target": "yang",\n  "status": "success",\n  "output": []\n}'


def test_skipping(tmp_path, monkeypatch, capsys):
    report = tmp_path.joinpath("report")

    def mock_recursive_fetch_script(*_):
        yield "test", zebr0_script.Status.SUCCESS, report

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)

    zebr0_script.run("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'skipping: "test"\n'
    assert not report.exists()


def test_ko(tmp_path, monkeypatch, capsys):
    report1 = tmp_path.joinpath("report1")
    report2 = tmp_path.joinpath("report2")
    report3 = tmp_path.joinpath("report3")

    def mock_recursive_fetch_script(*_):
        yield "one", zebr0_script.Status.PENDING, report1
        yield {"key": "yin", "target": "yang"}, zebr0_script.Status.PENDING, report2
        yield "two", zebr0_script.Status.PENDING, report3

    def mock_execute(command, *_):
        return {"command": command, "status": zebr0_script.Status.SUCCESS, "output": []}

    def mock_fetch_to_disk(_, key, target):
        return {"key": key, "target": target, "status": zebr0_script.Status.FAILURE, "output": ["multiline", "error", "output"]}

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr(zebr0_script, "execute", mock_execute)
    monkeypatch.setattr(zebr0_script, "fetch_to_disk", mock_fetch_to_disk)

    zebr0_script.run("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'executing: "one"\nsuccess: "one"\nexecuting: {"key": "yin", "target": "yang"}\nmultiline\nerror\noutput\nerror: {"key": "yin", "target": "yang"}\n'
    assert report1.exists()
    assert report2.exists()
    assert not report3.exists()


def test_redo(tmp_path, monkeypatch, capsys):
    report = tmp_path.joinpath("report")

    def mock_recursive_fetch_script(*_):
        yield "test", zebr0_script.Status.FAILURE, report

    def mock_execute(command, *_):
        return {"command": command, "status": zebr0_script.Status.SUCCESS, "output": []}

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr(zebr0_script, "execute", mock_execute)

    zebr0_script.run("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'executing: "test"\nsuccess: "test"\n'
    assert report.exists()
