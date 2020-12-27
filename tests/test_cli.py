import datetime

import pytest
import zebr0

import zebr0_script


@pytest.fixture(scope="module")
def server():
    with zebr0.TestServer() as server:
        yield server


def format_mtime(path):
    return datetime.datetime.fromtimestamp(path.stat().st_mtime).strftime("%c")


def test_ok(server, tmp_path, capsys):
    server.data = {"script": ["echo one", "sleep 1 && echo two"]}

    configuration_file = tmp_path.joinpath("zebr0.conf")
    zebr0.Client("http://127.0.0.1:8000", ["lorem", "ipsum"], 1).save_configuration(configuration_file)
    reports_path = tmp_path.joinpath("reports")

    zebr0_script.main(["-r", str(reports_path), "log"])
    assert capsys.readouterr().out == ""

    zebr0_script.main(["-f", str(configuration_file), "-r", str(reports_path), "show"])
    assert capsys.readouterr().out == 'todo: "echo one"\ntodo: "sleep 1 && echo two"\n'

    zebr0_script.main(["-f", str(configuration_file), "-r", str(reports_path), "run"])
    assert capsys.readouterr().out == 'executing: "echo one"\none\nsuccess: "echo one"\nexecuting: "sleep 1 && echo two"\ntwo\nsuccess: "sleep 1 && echo two"\n'

    report1_date = format_mtime(reports_path.joinpath("a885d7b3306acd60490834d5fdd234b5"))
    report2_date = format_mtime(reports_path.joinpath("7ab9b46af97310796a1918713345d986"))

    zebr0_script.main(["-r", str(reports_path), "log"])
    assert capsys.readouterr().out == "a885d7b3306acd60490834d5fdd234b5 " + report1_date + ' {\n  "command": "echo one",\n  "stdout": [\n    "one"\n  ]\n}\n7ab9b46af97310796a1918713345d986 ' + report2_date + ' {\n  "command": "sleep 1 && echo two",\n  "stdout": [\n    "two"\n  ]\n}\n'

    zebr0_script.main(["-f", str(configuration_file), "-r", str(reports_path), "show"])
    assert capsys.readouterr().out == 'done: "echo one"\ndone: "sleep 1 && echo two"\n'

    zebr0_script.main(["-f", str(configuration_file), "-r", str(reports_path), "run"])
    assert capsys.readouterr().out == 'skipping: "echo one"\nskipping: "sleep 1 && echo two"\n'
