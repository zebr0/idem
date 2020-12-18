import zebr0_script


def test_ok(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(zebr0_script, "shell", lambda _: (0, []))
    history_file = tmp_path.joinpath("history-file")

    zebr0_script.execute("./global-thermonuclear-war", history_file)

    assert capsys.readouterr().out == "done\n"
    assert history_file.read_text() == "./global-thermonuclear-war"


def test_ko(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(zebr0_script, "shell", lambda _: (1, []))
    history_file = tmp_path.joinpath("history-file")

    zebr0_script.execute("./global-thermonuclear-war", history_file, attempts=5, delay=0.1)

    assert capsys.readouterr().out == "retrying\nretrying\nretrying\nretrying\nerror\n"
    assert not history_file.exists()


def test_ko_then_ok(monkeypatch, tmp_path, capsys):
    variable = {"count": 0}  # a little trick since you can't update a normal "int" in mock_shell()

    def mock_shell(_):
        new_count = variable["count"] + 1
        if new_count != 3:
            variable["count"] = new_count
            return 1, []
        else:
            return 0, []

    monkeypatch.setattr(zebr0_script, "shell", mock_shell)
    history_file = tmp_path.joinpath("history-file")

    zebr0_script.execute("./global-thermonuclear-war", history_file, delay=0.1)

    assert capsys.readouterr().out == "retrying\nretrying\ndone\n"
    assert history_file.read_text() == "./global-thermonuclear-war"
