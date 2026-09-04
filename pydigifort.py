"""Cliente Python para a Digifort HTTP API 1.10.

Exemplo mínimo::

    from pydigifort import Servidor

    servidor = Servidor("192.168.0.10", 8601, ("admin", "senha"))
    print(servidor.versao_api())
    cameras = servidor.cameras.listar()

A API Digifort usa GET para a maioria dos comandos. O método ``request``
continua disponível para qualquer endpoint ou parâmetro não encapsulado.
"""

from __future__ import annotations

import base64
import hashlib
import json
import ssl
import threading
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping, Optional

__all__ = [
    "AuthConfig", "DigifortError", "DigifortHTTPError", "DigifortAPIError",
    "DigifortResponse", "Servidor",
]


class DigifortError(Exception):
    """Erro base do cliente Digifort."""


class DigifortHTTPError(DigifortError):
    """Falha de transporte HTTP, DNS, TLS ou timeout."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


class DigifortAPIError(DigifortError):
    """A API retornou ``Response.Code`` diferente de zero."""

    def __init__(self, code: Any, message: str, response: "DigifortResponse"):
        super().__init__(f"Digifort API error {code}: {message}")
        self.code, self.message, self.response = code, message, response


@dataclass(frozen=True)
class AuthConfig:
    """Credenciais e modo de autenticação.

    ``mode`` pode ser ``safe`` (recomendado), ``basic_http`` ou
    ``basic_params`` (não recomendado, pois envia a senha na URL).
    """

    username: str
    password: str
    mode: str = "safe"


@dataclass
class DigifortResponse:
    """Resposta normalizada sem perder os dados originais."""

    code: Any
    message: str
    data: Any
    raw: Any
    status: int = 200
    headers: Mapping[str, str] | None = None

    @property
    def ok(self) -> bool:
        return str(self.code) in {"0", "OK", "ok"}

    def json(self) -> Any:
        """Retorna o payload de dados, sem o envelope ``Response``."""
        return self.data


class _Grupo:
    """Namespace leve para permitir ``servidor.cameras.listar()``."""

    def __init__(self, servidor: "Servidor", grupo: str):
        self._servidor, self._grupo = servidor, grupo

    def listar(self, **params: Any) -> Any:
        return self._servidor.request(f"/Interface/{self._grupo}/Get{self._grupo}", params=params).data

    def status(self, **params: Any) -> Any:
        return self._servidor.request(f"/Interface/{self._grupo}/GetStatus", params=params).data

    def ativar(self, **params: Any) -> Any:
        params = dict(params, Action="Activate")
        return self._servidor.request(f"/Interface/{self._grupo}/Activation", params=params).data

    def desativar(self, **params: Any) -> Any:
        params = dict(params, Action="Deactivate")
        return self._servidor.request(f"/Interface/{self._grupo}/Activation", params=params).data


class Servidor:
    """Conexão com um servidor Digifort.

    Args:
        hostname: IP ou nome DNS, com ou sem esquema ``http://``.
        port: Porta HTTP da interface (normalmente 8601).
        auth: ``AuthConfig``, tupla ``(usuario, senha)``, dicionário ou ``None``.
        scheme: ``http`` por padrão; use ``https`` quando configurado no servidor.
        response_format: ``JSON`` por padrão; também aceita ``XML`` e ``Text``.
        timeout: Timeout de cada requisição em segundos.
        verify_tls: Valida certificado TLS quando ``scheme=https``.
    """

    def __init__(self, hostname: str, port: int = 8601,
                 auth: AuthConfig | tuple[str, str] | Mapping[str, Any] | None = None,
                 *, scheme: str = "http", response_format: str = "JSON",
                 timeout: float = 30.0, verify_tls: bool = True,
                 user_agent: str = "pydigifort/1.0") -> None:
        if not hostname or not isinstance(port, int) or not (1 <= port <= 65535):
            raise ValueError("hostname e port devem ser válidos")
        parsed = urllib.parse.urlsplit(hostname if "://" in hostname else f"{scheme}://{hostname}")
        self.scheme = parsed.scheme or scheme
        self.hostname = parsed.hostname or hostname
        self.port = port if parsed.port is None else parsed.port
        self.base_url = f"{self.scheme}://{self.hostname}:{self.port}"
        self.response_format = response_format
        self.timeout = timeout
        self.verify_tls = verify_tls
        self.user_agent = user_agent
        self.auth = self._coerce_auth(auth)
        self._session_id: Optional[str] = None
        self._auth_data: Optional[str] = None
        self._nonce: Optional[str] = None
        self._auth_lock = threading.RLock()
        # Namespaces de uso frequente; request() cobre o restante da API.
        self.cameras = _Grupo(self, "Cameras")
        self.users = _Grupo(self, "Users")
        self.groups = _Grupo(self, "Groups")
        self.events = _Grupo(self, "Events")
        self.lpr = _Grupo(self, "LPR")
        self.analytics = _Grupo(self, "Analytics")
        self.maps = _Grupo(self, "Maps")
        self.monitors = _Grupo(self, "VirtualMatrix")

    @staticmethod
    def _coerce_auth(auth: Any) -> Optional[AuthConfig]:
        if auth is None:
            return None
        if isinstance(auth, AuthConfig):
            return auth
        if isinstance(auth, (tuple, list)) and len(auth) == 2:
            return AuthConfig(str(auth[0]), str(auth[1]))
        if isinstance(auth, Mapping):
            return AuthConfig(str(auth.get("username", auth.get("user", ""))),
                              str(auth.get("password", auth.get("pass", ""))),
                              str(auth.get("mode", "safe")))
        raise TypeError("auth deve ser AuthConfig, (usuario, senha), dict ou None")

    def _url(self, path: str, params: Mapping[str, Any]) -> str:
        path = "/" + path.lstrip("/")
        query = urllib.parse.urlencode([(k, str(v)) for k, v in params.items() if v is not None], doseq=True)
        return self.base_url + path + ("?" + query if query else "")

    def _ensure_safe_session(self) -> None:
        if not self.auth or self.auth.mode != "safe" or self._auth_data:
            return
        with self._auth_lock:
            if self._auth_data:
                return
            result = self._raw_request("/Interface/CreateAuthSession", {}, include_auth=False)
            session = result.data.get("Session", result.data) if isinstance(result.data, dict) else {}
            self._session_id = str(session.get("ID", session.get("Id", "")))
            self._nonce = str(session.get("NOnce", session.get("Nonce", "")))
            if not self._session_id or not self._nonce:
                raise DigifortError("CreateAuthSession não retornou ID e NOnce")
            password_hash = hashlib.md5(self.auth.password.encode()).hexdigest().upper()
            value = f"{self._nonce}:{self.auth.username.upper()}:{password_hash}"
            self._auth_data = hashlib.md5(value.encode()).hexdigest().upper()

    def _auth_params(self) -> MutableMapping[str, Any]:
        params: MutableMapping[str, Any] = {}
        if not self.auth:
            return params
        mode = self.auth.mode.lower()
        if mode == "safe":
            self._ensure_safe_session()
            params.update(AuthSession=self._session_id, AuthData=self._auth_data)
        elif mode == "basic_params":
            params.update(AuthUser=self.auth.username, AuthPass=self.auth.password)
        elif mode != "basic_http":
            raise ValueError("modo de autenticação deve ser safe, basic_http ou basic_params")
        return params

    def _parse(self, body: bytes, content_type: str) -> Any:
        text = body.decode("utf-8-sig", errors="replace")
        if "json" in content_type.lower() or text.lstrip().startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        if "xml" in content_type.lower() or text.lstrip().startswith("<"):
            try:
                def convert(node: ET.Element) -> Any:
                    children = list(node)
                    if not children:
                        return node.text or ""
                    out: dict[str, Any] = {}
                    for child in children:
                        value = convert(child)
                        if child.tag in out:
                            old = out[child.tag]
                            out[child.tag] = old + [value] if isinstance(old, list) else [old, value]
                        else:
                            out[child.tag] = value
                    return out
                return convert(ET.fromstring(text))
            except ET.ParseError:
                pass
        result: dict[str, str] = {}
        for line in text.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                result[key.strip()] = value.strip()
        return result if result else text

    @staticmethod
    def _envelope(payload: Any) -> tuple[Any, str, Any]:
        if isinstance(payload, dict):
            response = payload.get("Response", payload)
            if isinstance(response, dict):
                return response.get("Code", response.get("RESPONSE_CODE", 0)), str(response.get("Message", response.get("RESPONSE_MESSAGE", ""))), response.get("Data", response)
            if "RESPONSE_CODE" in payload:
                return payload["RESPONSE_CODE"], str(payload.get("RESPONSE_MESSAGE", "")), payload
        return 0, "OK", payload

    def _raw_request(self, path: str, params: Mapping[str, Any], *, method: str = "GET",
                     data: Any = None, headers: Optional[Mapping[str, str]] = None,
                     include_auth: bool = True, binary: bool = False) -> DigifortResponse:
        query: dict[str, Any] = dict(params)
        if include_auth and self.auth and self.auth.mode == "safe":
            self._ensure_safe_session()
        if include_auth:
            query.update(self._auth_params())
        query.setdefault("ResponseFormat", self.response_format)
        request_headers = {"User-Agent": self.user_agent, "Accept": "application/json, application/xml, text/plain"}
        if headers:
            request_headers.update(headers)
        if self.auth and self.auth.mode == "basic_http":
            token = base64.b64encode(f"{self.auth.username}:{self.auth.password}".encode()).decode()
            request_headers["Authorization"] = f"Basic {token}"
        body = None
        if data is not None:
            if isinstance(data, (bytes, bytearray)):
                body = bytes(data)
            elif isinstance(data, str):
                body = data.encode()
            else:
                body = json.dumps(data).encode()
            request_headers.setdefault("Content-Type", "application/json")
        request = urllib.request.Request(self._url(path, query), data=body, headers=request_headers, method=method.upper())
        context = None if self.verify_tls else ssl._create_unverified_context()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout, context=context) as response:
                raw = response.read()
                if binary:
                    return DigifortResponse(0, "OK", raw, raw, response.status, dict(response.headers.items()))
                parsed = self._parse(raw, response.headers.get("Content-Type", ""))
                code, message, result_data = self._envelope(parsed)
                return DigifortResponse(code, message, result_data, parsed, response.status, dict(response.headers.items()))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise DigifortHTTPError(f"HTTP {exc.code} em {path}: {detail[:500]}", exc.code) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise DigifortHTTPError(f"Falha ao acessar {self.base_url}: {exc}") from exc

    def request(self, path: str, params: Optional[Mapping[str, Any]] = None, *, method: str = "GET",
                data: Any = None, headers: Optional[Mapping[str, str]] = None,
                raise_for_status: bool = True, binary: bool = False) -> DigifortResponse:
        """Envia uma requisição para qualquer caminho da API."""
        try:
            response = self._raw_request(path, params or {}, method=method, data=data, headers=headers, binary=binary)
        except DigifortAPIError:
            raise
        if raise_for_status and not response.ok:
            # Sessões seguras expiram em 60 s; refaz uma vez transparentemente.
            if self.auth and self.auth.mode == "safe":
                self._session_id = self._auth_data = self._nonce = None
                response = self._raw_request(path, params or {}, method=method, data=data, headers=headers, binary=binary)
            if not response.ok:
                raise DigifortAPIError(response.code, response.message, response)
        return response

    def manter_sessao(self) -> DigifortResponse:
        """Mantém aberta a sessão segura Digifort por mais 60 segundos."""
        self._ensure_safe_session()
        return self.request("/Interface/UpdateAuthSession", {"AuthSession": self._session_id, "AuthData": self._auth_data})

    def versao_api(self) -> Any:
        return self.request("/Interface/GetAPIVersion").data

    def informacoes_servidor(self) -> Any:
        return self.request("/Interface/Server/GetServerInfo").data

    def codigo_maquina(self) -> Any:
        return self.request("/Interface/Server/GetMachineCode").data

    def licenciamento(self, **params: Any) -> Any:
        return self.request("/Interface/Server/GetLicenseInfo", params).data

    def uso_servidor(self, **params: Any) -> Any:
        return self.request("/Interface/Server/GetServerUsage", params).data

    def listar_cameras(self, **params: Any) -> Any:
        return self.request("/Interface/Cameras/GetCameras", params).data

    def status_cameras(self, **params: Any) -> Any:
        return self.request("/Interface/Cameras/GetCameraStatus", params).data

    def snapshot(self, camera: str, **params: Any) -> bytes:
        """Obtém e retorna os bytes da imagem JPEG da câmera."""
        response = self.request("/Interface/Cameras/GetSnapshot", dict(params, Camera=camera), binary=True)
        return response.data

    def endpoint(self, path: str, **params: Any) -> Any:
        """Alias explícito para chamar comandos ainda não encapsulados."""
        return self.request(path, params).data

    def __repr__(self) -> str:
        return f"Servidor({self.hostname!r}, {self.port}, auth={bool(self.auth)})"
