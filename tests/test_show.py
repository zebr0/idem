from pathlib import Path

import zebr0_script


def test_ok(tmp_path, monkeypatch, capsys):
    report1 = tmp_path.joinpath("report1")
    report2 = tmp_path.joinpath("report2")

    def mock_recursive_fetch_script(*_):
        yield "one", report1
        yield "two", report2

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)

    zebr0_script.show("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'todo: "one"\ntodo: "two"\n'

    report1.touch()
    zebr0_script.show("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'done: "one"\ntodo: "two"\n'

    report2.touch()
    zebr0_script.show("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'done: "one"\ndone: "two"\n'
