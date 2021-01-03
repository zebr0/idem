from pathlib import Path

import zebr0_script


def test_multiple_pending(tmp_path, monkeypatch, capsys):
    def mock_recursive_fetch_script(*_):
        yield "one", zebr0_script.Status.PENDING, tmp_path.joinpath("report1")
        yield "two", zebr0_script.Status.PENDING, tmp_path.joinpath("report2")

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)

    zebr0_script.show("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'pending: "one"\npending: "two"\n'


def test_success(tmp_path, monkeypatch, capsys):
    def mock_recursive_fetch_script(*_):
        yield "command", zebr0_script.Status.SUCCESS, tmp_path.joinpath("report")

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)

    zebr0_script.show("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'success: "command"\n'


def test_failure(tmp_path, monkeypatch, capsys):
    def mock_recursive_fetch_script(*_):
        yield "command", zebr0_script.Status.FAILURE, tmp_path.joinpath("report")

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)

    zebr0_script.show("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == 'failure: "command"\n'
