import datetime
import time

import zebr0_script


def test_reports_path_doesnt_exist(tmp_path, capsys):
    reports_path = tmp_path.joinpath("reports")

    zebr0_script.log(reports_path)
    assert capsys.readouterr().out == ""


def get_strftime(path):
    return datetime.datetime.fromtimestamp(path.stat().st_mtime).strftime("%c")


def test_ok(tmp_path, capsys):
    report1 = tmp_path.joinpath("report1")
    report1.write_text("one\n")
    time.sleep(0.1)
    report2 = tmp_path.joinpath("report2")
    report2.write_text("two\n")

    zebr0_script.log(tmp_path)
    assert capsys.readouterr().out == "report1 " + get_strftime(report1) + " one\nreport2 " + get_strftime(report2) + " two\n"
