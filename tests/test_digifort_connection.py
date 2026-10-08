import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from services.application import DigifortConfig


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()
        self.headers = {"Content-Type": "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return self.payload


def test_configured_digifort_connection_uses_documented_endpoint_and_safe_auth():
    config = DigifortConfig(
        name="Servidor teste",
        hostname="192.0.2.12",
        port=8601,
        username="admin",
        password="secret",
        auth_mode="safe",
    )
    client = config.client()
    replies = [
        {
            "Response": {
                "Code": 0,
                "Message": "OK",
                "Data": {"Session": {"ID": 7, "NONCE": "ABC"}},
            }
        },
        {"Response": {"Code": 0, "Message": "OK", "Data": {"Version": "7.4"}}},
    ]

    with patch(
        "services.pydigifort.urllib.request.urlopen",
        side_effect=[FakeResponse(payload) for payload in replies],
    ) as urlopen:
        result = client.informacoes_servidor()

    assert client.hostname == config.hostname
    assert client.port == config.port
    assert client.auth.username == config.username
    assert client.auth.password == config.password
    assert client.auth.mode == config.auth_mode
    assert result == {"Version": "7.4"}

    session_request = urlopen.call_args_list[0].args[0]
    info_request = urlopen.call_args_list[1].args[0]
    assert urlsplit(session_request.full_url).path == "/Interface/CreateAuthSession"
    parsed_info_url = urlsplit(info_request.full_url)
    assert parsed_info_url.path == "/Interface/Server/GetInfo"
    query = parse_qs(parsed_info_url.query)
    expected_password_hash = hashlib.md5(b"secret").hexdigest().upper()
    expected_auth_data = hashlib.md5(f"ABC:ADMIN:{expected_password_hash}".encode()).hexdigest().upper()
    assert query["AuthSession"] == ["7"]
    assert query["AuthData"] == [expected_auth_data]
    assert query["ResponseFormat"] == ["JSON"]


def test_documented_api_methods_use_reference_endpoints():
    from services.pydigifort import Servidor

    client = Servidor("192.0.2.12")
    endpoints = [
        (client.versao_api, "/Interface/GetAPIVersion"),
        (client.informacoes_servidor, "/Interface/Server/GetInfo"),
        (client.licenciamento, "/Interface/Server/GetLicenses"),
        (client.uso_servidor, "/Interface/Server/GetUsage"),
        (client.listar_cameras, "/Interface/Cameras/GetCameras"),
        (client.status_cameras, "/Interface/Cameras/GetStatus"),
        (client.cameras.listar, "/Interface/Cameras/GetCameras"),
        (client.cameras.status, "/Interface/Cameras/GetStatus"),
        (client.users.listar, "/Interface/Users/GetUsers"),
        (client.groups.listar, "/Interface/Users/GetGroups"),
        (client.events.listar, "/Interface/GlobalEvents/GetGlobalEvents"),
        (client.analytics.listar, "/Interface/Analytics/GetAnalyticsConfigurations"),
        (client.analytics.status, "/Interface/Analytics/GetStatus"),
        (client.lpr.listar, "/Interface/LPR/GetLPRConfigurations"),
        (client.monitors.listar, "/Interface/VirtualMatrix/GetActiveMonitors"),
    ]
    calls = []

    def fake_request(path, params=None, **kwargs):
        calls.append(path)
        return type("Response", (), {"data": {}})()

    client.request = fake_request
    for operation, _ in endpoints:
        operation()

    assert calls == [expected for _, expected in endpoints]
