"""Carregamento local de segredos do Vault Site.

O arquivo ``.env`` fica fora do controle de versão. Em produção, as mesmas
variáveis podem ser injetadas pelo ambiente do processo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatabaseSecret:
    hostname: str = r"localhost\sqlexpress"
    database: str = "DataDBEnt"
    driver: str = "ODBC Driver 18 for SQL Server"
    username: str = ""
    password: str = ""

    @property
    def auth(self) -> tuple[str, str] | None:
        return (self.username, self.password) if self.username else None

    def vault_kwargs(self) -> dict[str, object]:
        return {
            "hostname": self.hostname,
            "database": self.database,
            "driver": self.driver,
            "auth": self.auth,
        }


def load_database_secret(path: str | Path | None = None) -> DatabaseSecret:
    """Carrega ``.env`` sem dependência externa; variáveis do ambiente têm prioridade."""
    values: dict[str, str] = {}
    env_path = Path(path) if path else Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        for raw in env_path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")

    def value(key: str, default: str) -> str:
        return os.getenv(key, values.get(key, default))

    return DatabaseSecret(
        hostname=value("VAULT_SQL_HOSTNAME", r"localhost\sqlexpress"),
        database=value("VAULT_SQL_DATABASE", "DataDBEnt"),
        driver=value("VAULT_SQL_DRIVER", "ODBC Driver 18 for SQL Server"),
        username=value("VAULT_SQL_USERNAME", ""),
        password=value("VAULT_SQL_PASSWORD", ""),
    )


def save_database_secret(secret: DatabaseSecret, path: str | Path | None = None) -> Path:
    """Persiste a configuração do banco no arquivo secreto local."""
    env_path = Path(path) if path else Path(__file__).resolve().parents[2] / ".env"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join([
        "# Segredo local — não versionar este arquivo.",
        f"VAULT_SQL_HOSTNAME={secret.hostname}",
        f"VAULT_SQL_DATABASE={secret.database}",
        f"VAULT_SQL_DRIVER={secret.driver}",
        f"VAULT_SQL_USERNAME={secret.username}",
        f"VAULT_SQL_PASSWORD={secret.password}",
        "",
    ])
    env_path.write_text(content, encoding="utf-8")
    return env_path
