from pathlib import Path

import pytest
import zebr0

import zebr0_script


@pytest.fixture(scope="module")
def server():
    with zebr0.TestServer() as server:
        yield server


def test_ok(server, tmp_path, capsys):
    server.data = {"script": ["install package xxx",
                              {"key": "configuration-file", "target": "/etc/xxx/conf.ini"},
                              "chmod 400 /etc/xxx/conf.ini",
                              {"include": "second-script"},
                              {"make-coffee": "black"}],
                   "second-script": ["install package yyy",
                                     "yyy configure network"]}
    client = zebr0.Client("http://localhost:8000", configuration_file=Path(""))

    result = zebr0_script.recursive_fetch_script(client, "script", tmp_path)
    assert list(result) == [("install package xxx", zebr0_script.Status.PENDING, tmp_path.joinpath("e60305c56524b749c03a2c648d33e791")),
                            ({"key": "configuration-file", "target": "/etc/xxx/conf.ini"}, zebr0_script.Status.PENDING, tmp_path.joinpath("c065878911c6b3beee171d12fed19aa2")),
                            ("chmod 400 /etc/xxx/conf.ini", zebr0_script.Status.PENDING, tmp_path.joinpath("8b982863e398cfbe84dc334c3b02164a")),
                            ("install package yyy", zebr0_script.Status.PENDING, tmp_path.joinpath("a71c44f4d35f54f68fe8930a1c29148f")),
                            ("yyy configure network", zebr0_script.Status.PENDING, tmp_path.joinpath("f55c297fd62c279cf13b0e2e40aac570"))]
    assert capsys.readouterr().out == 'malformed task, ignored: {"make-coffee": "black"}\n'


def test_ko_key_not_found(server, tmp_path, capsys):
    server.data = {}
    client = zebr0.Client("http://localhost:8000", configuration_file=Path(""))

    result = zebr0_script.recursive_fetch_script(client, "script", tmp_path)
    assert list(result) == []
    assert capsys.readouterr().out == "key 'script' not found on server http://localhost:8000\n"


def test_ko_not_a_script(server, tmp_path, capsys):
    server.data = {"script": "not a script"}
    client = zebr0.Client("http://localhost:8000", configuration_file=Path(""))

    result = zebr0_script.recursive_fetch_script(client, "script", tmp_path)
    assert list(result) == []
    assert capsys.readouterr().out == "key 'script' on server http://localhost:8000 is not a proper yaml or json list\n"


def test_ok_include_key_not_found(server, tmp_path, capsys):
    server.data = {"script": [{"include": "second-script"},
                              "install package xxx"]}
    client = zebr0.Client("http://localhost:8000", configuration_file=Path(""))

    result = zebr0_script.recursive_fetch_script(client, "script", tmp_path)
    assert list(result) == [("install package xxx", zebr0_script.Status.PENDING, tmp_path.joinpath("e60305c56524b749c03a2c648d33e791"))]
    assert capsys.readouterr().out == "key 'second-script' not found on server http://localhost:8000\n"


def test_ok_include_not_a_script(server, tmp_path, capsys):
    server.data = {"script": [{"include": "second-script"},
                              "install package xxx"],
                   "second-script": "not a script"}
    client = zebr0.Client("http://localhost:8000", configuration_file=Path(""))

    result = zebr0_script.recursive_fetch_script(client, "script", tmp_path)
    assert list(result) == [("install package xxx", zebr0_script.Status.PENDING, tmp_path.joinpath("e60305c56524b749c03a2c648d33e791"))]
    assert capsys.readouterr().out == "key 'second-script' on server http://localhost:8000 is not a proper yaml or json list\n"


def test_ok_status_success(server, tmp_path, capsys):
    server.data = {"script": ["install package xxx"]}
    client = zebr0.Client("http://localhost:8000", configuration_file=Path(""))

    report_path = tmp_path.joinpath("e60305c56524b749c03a2c648d33e791")
    report_path.write_text('{"status": "success"}')

    result = zebr0_script.recursive_fetch_script(client, "script", tmp_path)
    assert list(result) == [("install package xxx", zebr0_script.Status.SUCCESS, report_path)]
    assert capsys.readouterr().out == ""


def test_ok_status_failure(server, tmp_path, capsys):
    server.data = {"script": ["install package xxx"]}
    client = zebr0.Client("http://localhost:8000", configuration_file=Path(""))

    report_path = tmp_path.joinpath("e60305c56524b749c03a2c648d33e791")
    report_path.write_text('{"status": "failure"}')

    result = zebr0_script.recursive_fetch_script(client, "script", tmp_path)
    assert list(result) == [("install package xxx", zebr0_script.Status.FAILURE, report_path)]
    assert capsys.readouterr().out == ""
