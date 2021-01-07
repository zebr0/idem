import datetime
import time

import zebr0_script


def test_reports_path_doesnt_exist(tmp_path, capsys):
    reports_path = tmp_path.joinpath("reports")

    zebr0_script.log(reports_path)
    assert capsys.readouterr().out == ""


def format_mtime(path):
    return datetime.datetime.fromtimestamp(path.stat().st_mtime).strftime("%c")


OK_REPORT1 = """{
  "command": "install package xxx",
  "status": "success",
  "output": [
    "Lorem ipsum dolor sit amet"
  ]
}"""

OK_REPORT2 = """{
  "key": "configuration-file",
  "target": "/etc/xxx/conf.ini",
  "status": "success",
  "output": [
    "consectetur adipiscing elit"
  ]
}"""

OK_OUTPUT = """
e60305c56524b749c03a2c648d33e791 {} {{"command": "install package xxx", "status": "success"}}
c065878911c6b3beee171d12fed19aa2 {} {{"key": "configuration-file", "target": "/etc/xxx/conf.ini", "status": "success"}}
""".lstrip()


def test_ok(tmp_path, capsys):
    report1 = tmp_path.joinpath("e60305c56524b749c03a2c648d33e791")
    report1.write_text(OK_REPORT1)
    time.sleep(0.1)
    report2 = tmp_path.joinpath("c065878911c6b3beee171d12fed19aa2")
    report2.write_text(OK_REPORT2)

    zebr0_script.log(tmp_path)
    assert capsys.readouterr().out == OK_OUTPUT.format(format_mtime(report1), format_mtime(report2))
