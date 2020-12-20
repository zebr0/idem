import zebr0_script


def test_ok(monkeypatch, capsys):
    monkeypatch.setattr(zebr0_script, "shell", lambda _: (0, []))

    assert zebr0_script.execute("./global-thermonuclear-war") == "./global-thermonuclear-war"

    assert capsys.readouterr().out == ""


def test_ko(monkeypatch, capsys):
    monkeypatch.setattr(zebr0_script, "shell", lambda _: (1, []))

    assert not zebr0_script.execute("./global-thermonuclear-war", attempts=5, delay=0.1)

    assert capsys.readouterr().out == "retrying\nretrying\nretrying\nretrying\n"


def test_ko_then_ok(monkeypatch, capsys):
    variable = {"count": 0}  # a little trick since you can't update a normal "int" in mock_shell()

    def mock_shell(_):
        new_count = variable["count"] + 1
        if new_count != 3:
            variable["count"] = new_count
            return 1, []
        else:
            return 0, []

    monkeypatch.setattr(zebr0_script, "shell", mock_shell)

    assert zebr0_script.execute("./global-thermonuclear-war", delay=0.1) == "./global-thermonuclear-war"

    assert capsys.readouterr().out == "retrying\nretrying\n"
