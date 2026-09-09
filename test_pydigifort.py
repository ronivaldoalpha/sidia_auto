import base64
import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src" / "services"))

from pydigifort import AuthConfig, DigifortAPIError, Servidor

seen = []
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        seen.append((urlparse(self.path).path, query, self.headers.get("Authorization")))
        if urlparse(self.path).path.endswith("CreateAuthSession"):
            payload = {"Response": {"Code": 0, "Message": "OK", "Data": {"Session": {"ID": 7, "NOnce": "ABC"}}}}
        elif urlparse(self.path).path.endswith("GetAPIVersion"):
            payload = {"Response": {"Code": 0, "Message": "OK", "Data": {"ApiVersion": {"Major": 1}}}}
        elif urlparse(self.path).path.endswith("GetCameras"):
            payload = {"Response": {"Code": 0, "Message": "OK", "Data": {"Cameras": [{"Name": "Cam1"}]}}}
        else:
            payload = {"Response": {"Code": 42, "Message": "Nope"}}
        raw = json.dumps(payload).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def log_message(self, *_): pass

server = HTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    port = server.server_address[1]
    client = Servidor("127.0.0.1", port, ("admin", "pass"))
    assert client.versao_api()["ApiVersion"]["Major"] == 1
    assert client.cameras.listar()["Cameras"][0]["Name"] == "Cam1"
    expected = hashlib.md5(("ABC:ADMIN:" + hashlib.md5(b"pass").hexdigest().upper()).encode()).hexdigest().upper()
    assert seen[1][1]["AuthSession"] == ["7"] and seen[1][1]["AuthData"] == [expected]
    try: client.endpoint("/Interface/Unknown")
    except DigifortAPIError as exc: assert exc.code == 42
    else: raise AssertionError("APIError não lançado")
    basic = Servidor("127.0.0.1", port, AuthConfig("u", "p", "basic_http"))
    basic.versao_api()
    assert seen[-1][2] == "Basic " + base64.b64encode(b"u:p").decode()
finally:
    server.shutdown()
print("ok")
