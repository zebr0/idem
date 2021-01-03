from pathlib import Path

import pytest
import zebr0

import zebr0_script


@pytest.fixture(scope="module")
def server():
    with zebr0.TestServer() as server:
        yield server


def test_ok(server, tmp_path, capsys):
    server.data = {"dummy.conf": "yin: yang\n"}
    client = zebr0.Client("http://localhost:8000", configuration_file=Path(""))
    target = tmp_path.joinpath("many/directories/file")

    assert zebr0_script.fetch_to_disk(client, "dummy.conf", target) == {"key": "dummy.conf", "target": target, "status": zebr0_script.Status.SUCCESS, "output": []}
    assert target.read_text() == "yin: yang\n"
    assert capsys.readouterr().out == ""


def test_ko_key_not_found(server, tmp_path, capsys):
    server.data = {}
    client = zebr0.Client("http://localhost:8000", configuration_file=Path(""))
    target = tmp_path.joinpath("many/directories/file")

    assert zebr0_script.fetch_to_disk(client, "dummy.conf", target) == {"key": "dummy.conf", "target": target, "status": zebr0_script.Status.FAILURE, "output": ["key 'dummy.conf' not found on server http://localhost:8000"]}
    assert not target.exists()
    assert capsys.readouterr().out == ""


def test_ko_oserror(server, capsys):
    server.data = {"dummy.conf": "yin: yang\n"}
    client = zebr0.Client("http://localhost:8000", configuration_file=Path(""))

    assert zebr0_script.fetch_to_disk(client, "dummy.conf", "") == {"key": "dummy.conf", "target": "", "status": zebr0_script.Status.FAILURE, "output": ["[Errno 21] Is a directory: '.'"]}
    assert capsys.readouterr().out == ""
