from pathlib import Path

import zebr0_script

TEST_OK_STDOUT = """
success: "one"
failure: "two"
pending: {"key": "yin", "target": "yang"}
""".lstrip()


def test_ok(tmp_path, monkeypatch, capsys):
    def mock_recursive_fetch_script(*_):
        yield "one", zebr0_script.Status.SUCCESS, tmp_path.joinpath("report1")
        yield "two", zebr0_script.Status.FAILURE, tmp_path.joinpath("report2")
        yield {"key": "yin", "target": "yang"}, zebr0_script.Status.PENDING, tmp_path.joinpath("report3")

    monkeypatch.setattr(zebr0_script, "recursive_fetch_script", mock_recursive_fetch_script)

    zebr0_script.show("http://localhost:8001", [], 1, Path(""), tmp_path, "script")
    assert capsys.readouterr().out == TEST_OK_STDOUT
