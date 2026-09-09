"""Tratamento de erros operacionais e log local de fallback.

O logger não depende do SQL Server. Assim, uma falha de conexão ainda fica
registrada em ``storage/logs/application.log``.
"""

from __future__ import annotations

import json
import re
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError, SQLAlchemyError


_LOG_PATH = Path(__file__).resolve().parents[2] / "storage" / "logs" / "application.log"


@dataclass(frozen=True)
class ErrorInfo:
    user_message: str
    detail: str
    error_type: str
    is_database: bool = False
    is_credential: bool = False


def _redact(value: str) -> str:
    """Remove senhas comuns antes de gravar detalhes no log local."""
    value = re.sub(r"(?i)(password|pwd|senha)([=:'\"]+)[^;,)\s]+", r"\1\2***", value)
    value = re.sub(r"(?i)(AuthPass|VAULT_SQL_PASSWORD)([=:'\"]+)[^&;\s]+", r"\1\2***", value)
    return value


def classify_error(exc: BaseException, *, operation: str = "operação") -> ErrorInfo:
    detail = _redact(str(exc) or repr(exc))
    lower = detail.casefold()
    database = isinstance(exc, (SQLAlchemyError, DBAPIError, InterfaceError, OperationalError)) or any(
        token in lower for token in ("pyodbc", "sql server", "sqlalchemy", "odbc", "database", "banco de dados")
    )
    credential = any(token in lower for token in ("18456", "28000", "4060", "401", "403", "login failed", "falha de logon", "credential", "credencial", "senha"))
    if database and credential:
        message = "Banco de dados não está conectado: credenciais inválidas ou banco sem acesso."
    elif database:
        message = "Banco de dados não está conectado. Verifique o SQL Server e a configuração do arquivo secreto."
    elif credential:
        message = f"Credencial inválida ao executar {operation}."
    else:
        message = f"Não foi possível executar {operation}."
    return ErrorInfo(message, detail, type(exc).__name__, database, credential)


def log_error(operation: str, exc: BaseException, *, context: dict[str, Any] | None = None) -> ErrorInfo:
    info = classify_error(exc, operation=operation)
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "error_type": info.error_type,
        "user_message": info.user_message,
        "detail": info.detail,
        "context": {key: _redact(str(value)) for key, value in (context or {}).items()},
        "traceback": _redact("".join(traceback.format_exception(exc))),
    }
    with _LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return info


def log_path() -> Path:
    return _LOG_PATH
