import zebr0_script


def test_ok(monkeypatch, capsys):
    monkeypatch.setattr(zebr0_script, "shell", lambda _: (0, ["hello", "world"]))

    assert zebr0_script.execute("./global-thermonuclear-war") == ["hello", "world"]

    assert capsys.readouterr().out == ""


def test_ko(monkeypatch, capsys):
    monkeypatch.setattr(zebr0_script, "shell", lambda _: (1, []))

    assert zebr0_script.execute("./global-thermonuclear-war", attempts=3, pause=0.1) is None

    assert capsys.readouterr().out == "failed, 2 attempts remaining, will try again in 0.1 seconds\nfailed, 1 attempts remaining, will try again in 0.1 seconds\n"


def test_ko_then_ok(monkeypatch, capsys):
    variable = {"count": 0}  # a little trick since you can't update a normal "int" in mock_shell()

    def mock_shell(_):
        new_count = variable["count"] + 1
        if new_count != 3:
            variable["count"] = new_count
            return 1, []
        else:
            return 0, ["hello", "world"]

    monkeypatch.setattr(zebr0_script, "shell", mock_shell)

    assert zebr0_script.execute("./global-thermonuclear-war", pause=0.1) == ["hello", "world"]

    assert capsys.readouterr().out == "failed, 3 attempts remaining, will try again in 0.1 seconds\nfailed, 2 attempts remaining, will try again in 0.1 seconds\n"
