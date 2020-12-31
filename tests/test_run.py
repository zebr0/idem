from pathlib import Path

import zebr0_script

REPORT1_CONTENT = """{
  "command": "test",
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
        yield "test", report1
        yield {"key": "yin", "target": "yang"}, report2

    def mock_execute(command, *_):
        return {"command": command, "output": ["Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
                                               "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
                                               "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
                                               "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."]}

    def mock_fetch_to_disk(_, key, target):
        return {"key": key, "target": target}

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr(zebr0_script, "execute", mock_execute)
    monkeypatch.setattr(zebr0_script, "fetch_to_disk", mock_fetch_to_disk)

    zebr0_script.run("http://localhost:8001", [], 1, Path(""), reports_path, "script")
    assert capsys.readouterr().out == 'executing: "test"\nsuccess: "test"\nexecuting: {"key": "yin", "target": "yang"}\nsuccess: {"key": "yin", "target": "yang"}\n'
    assert report1.read_text() == REPORT1_CONTENT
    assert report2.read_text() == '{\n  "key": "yin",\n  "target": "yang"\n}'

    zebr0_script.run("http://localhost:8001", [], 1, Path(""), reports_path, "script")
    assert capsys.readouterr().out == 'skipping: "test"\nskipping: {"key": "yin", "target": "yang"}\n'


def test_ko(tmp_path, monkeypatch, capsys):
    report1 = tmp_path.joinpath("report1")
    report2 = tmp_path.joinpath("report2")
    report3 = tmp_path.joinpath("report3")

    def mock_recursive_fetch_script(*_):
        yield "one", report1
        yield "two", report2
        yield "three", report3

    def mock_execute(command, *_):
        if command == "one":
            return {"command": command, "output": []}

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)
    monkeypatch.setattr(zebr0_script, "execute", mock_execute)

    zebr0_script.run("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'executing: "one"\nsuccess: "one"\nexecuting: "two"\nerror: "two"\n'
    assert report1.exists()
    assert not report2.exists()
    assert not report3.exists()

    zebr0_script.run("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'skipping: "one"\nexecuting: "two"\nerror: "two"\n'
    assert report1.exists()
    assert not report2.exists()
    assert not report3.exists()
