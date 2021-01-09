import datetime
import io

import pytest
import zebr0

import zebr0_script


@pytest.fixture(scope="module")
def server():
    with zebr0.TestServer() as server:
        yield server


def format_mtime(path):
    return datetime.datetime.fromtimestamp(path.stat().st_mtime).strftime("%c")


OK_OUTPUT1 = """
pending: "echo one"
pending: "sleep 1 && echo two"
""".lstrip()

OK_OUTPUT2 = """
next: "echo one"
(e)xecute, (s)kip, or (q)uit?
.
success!
write report? (y)es or (n)o
next: "sleep 1 && echo two"
(e)xecute, (s)kip, or (q)uit?
""".lstrip()

OK_OUTPUT3 = """
executing: "echo one"
.
success!
executing: "sleep 1 && echo two"
.
success!
""".lstrip()

OK_OUTPUT4 = """
a885d7b3306acd60490834d5fdd234b5 {} {{"command": "echo one", "status": "success"}}
7ab9b46af97310796a1918713345d986 {} {{"command": "sleep 1 && echo two", "status": "success"}}
""".lstrip()

OK_OUTPUT5 = """
success: "echo one"
success: "sleep 1 && echo two"
""".lstrip()

OK_OUTPUT6 = """
skipping: "echo one"
skipping: "sleep 1 && echo two"
""".lstrip()


def test_ok(server, tmp_path, capsys, monkeypatch):
    server.data = {"script": ["echo one", "sleep 1 && echo two"]}

    configuration_file = tmp_path.joinpath("zebr0.conf")
    zebr0.Client("http://localhost:8000", ["lorem", "ipsum"], 1).save_configuration(configuration_file)
    reports_path = tmp_path.joinpath("reports")

    zebr0_script.main(f"-r {reports_path} log".split())
    assert capsys.readouterr().out == ""

    zebr0_script.main(f"-f {configuration_file} -r {reports_path} show".split())
    assert capsys.readouterr().out == OK_OUTPUT1

    monkeypatch.setattr("sys.stdin", io.StringIO("e\nn\nq\n"))
    zebr0_script.main(f"-f {configuration_file} -r {reports_path} debug".split())
    assert capsys.readouterr().out == OK_OUTPUT2

    zebr0_script.main(f"-f {configuration_file} -r {reports_path} run".split())
    assert capsys.readouterr().out == OK_OUTPUT3

    zebr0_script.main(f"-r {reports_path} log".split())
    assert capsys.readouterr().out == OK_OUTPUT4.format(format_mtime(reports_path.joinpath("a885d7b3306acd60490834d5fdd234b5")), format_mtime(reports_path.joinpath("7ab9b46af97310796a1918713345d986")))

    zebr0_script.main(f"-f {configuration_file} -r {reports_path} show".split())
    assert capsys.readouterr().out == OK_OUTPUT5

    zebr0_script.main(f"-f {configuration_file} -r {reports_path} run".split())
    assert capsys.readouterr().out == OK_OUTPUT6
