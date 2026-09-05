from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, TYPE_CHECKING

# As bibliotecas legadas ficam na raiz do projeto e continuam reutilizáveis.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

if TYPE_CHECKING:
    from services.PyVaultsiteDB import Vault
    from services.pydigifort import Servidor


@dataclass
class DigifortConfig:
    name: str
    hostname: str
    port: int = 8601
    username: str = ""
    password: str = ""
    auth_mode: str = "safe"
    enabled: bool = True

    def client(self) -> Servidor:
        from services.pydigifort import AuthConfig, Servidor
        auth = AuthConfig(self.username, self.password, self.auth_mode) if self.username else None
        return Servidor(self.hostname, self.port, auth)


@dataclass
class ServiceHealth:
    name: str
    kind: str
    online: bool | None
    detail: str
    checked_at: datetime | None = None

    @property
    def label(self) -> str:
        return "ONLINE" if self.online is True else "OFF-LINE" if self.online is False else "NÃO VERIFICADO"


@dataclass
class AppState:
    digifort: list[DigifortConfig] = field(default_factory=list)
    health: dict[str, ServiceHealth] = field(default_factory=dict)
    selected_tag: str | None = None
    selected_camera: str | None = None
    alert_enabled: bool = False
    alert_event: str | None = None
    event_preferences: dict[str, str] = field(default_factory=dict)


class ApplicationService:
    """Orquestra banco, Digifort e dados temporários da UI."""

    def __init__(self) -> None:
        self.state = AppState()
        from services.PyVaultsiteDB import Vault
        self.database = Vault()
        self.event_types = [
            "Acesso Autorizado", "Acesso Negado", "Crachá Vencido",
            "Cartão Não Cadastrado", "Porta Forçada", "Porta Mantida Aberta",
        ]

    def controller_tags(self) -> list[dict[str, Any]]:
        """Retorna TagName/Desc distintos, preparados para a tabela de vínculo."""
        try:
            rows = self.database.controllers.listar(order_by="TagName")
        except Exception:
            rows = []
        unique: dict[str, dict[str, Any]] = {}
        for row in rows:
            tag = str(row.get("TagName") or "").strip()
            if tag and tag not in unique:
                unique[tag] = {"TagName": tag, "Desc": row.get("Desc") or "Sem descrição"}
        return list(unique.values())

    def cameras(self) -> list[str]:
        cameras: set[str] = set()
        for config in self.state.digifort:
            if not config.enabled:
                continue
            try:
                payload = config.client().listar_cameras()
                self._collect_names(payload, cameras)
            except Exception:
                continue
        return sorted(cameras, key=str.casefold)

    def _collect_names(self, value: Any, output: set[str]) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key.casefold() in {"name", "cameraname", "objectname"} and isinstance(item, str):
                    output.add(item)
                self._collect_names(item, output)
        elif isinstance(value, list):
            for item in value:
                self._collect_names(item, output)

    def add_digifort(self, config: DigifortConfig) -> None:
        self.state.digifort.append(config)

    def save_binding(self, tag: str, camera: str, server: str, alert: bool, event: str) -> tuple[bool, str]:
        """Persiste câmera/servidor/alerta no mapeamento existente.

        A tabela fornecida não possui coluna para o tipo do evento; por isso,
        o evento fica no estado da aplicação até a tabela de eventos ser
        documentada. O restante da definição é gravado em SQL Server.
        """
        try:
            current = self.database.mapeamentos.obter(TrController=tag)
            values = {"Cam1Nome": camera or None, "Cam1Server": server or None, "dig_alerta": alert}
            if current:
                self.database.mapeamentos.atualizar({"TrController": tag}, values)
            else:
                self.database.mapeamentos.criar(TrController=tag, **values)
            self.state.event_preferences[tag] = event
            return True, "Vínculo salvo; o tipo do evento está aguardando a tabela de eventos documentada."
        except Exception as exc:
            return False, f"Não foi possível salvar o vínculo: {exc}"

    def check_database(self) -> ServiceHealth:
        try:
            self.database.testar_conexao()
            health = ServiceHealth("Banco Vault Site", "database", True, "SQL Server respondeu SELECT 1", datetime.now())
        except Exception as exc:
            health = ServiceHealth("Banco Vault Site", "database", False, str(exc), datetime.now())
        self.state.health["database"] = health
        return health

    def check_digifort(self, config: DigifortConfig) -> ServiceHealth:
        try:
            payload = config.client().informacoes_servidor()
            detail = "GET ServerInfo respondeu corretamente"
            if payload:
                detail += f" • {str(payload)[:160]}"
            health = ServiceHealth(config.name, "digifort", True, detail, datetime.now())
        except Exception as exc:
            health = ServiceHealth(config.name, "digifort", False, str(exc), datetime.now())
        self.state.health[config.name] = health
        return health

    def check_all(self) -> list[ServiceHealth]:
        result = [self.check_database()]
        result.extend(self.check_digifort(item) for item in self.state.digifort if item.enabled)
        return result

    def metrics(self, start: datetime | None = None, end: datetime | None = None) -> dict[str, Any]:
        end = end or datetime.now()
        start = start or (end - timedelta(days=7))
        try:
            accuracy = self.database.taxa_acuracidade(inicio=start, fim=end)
        except Exception:
            accuracy = {"total_eventos": 0, "falhas": 0, "taxa_acuracidade": 0.0}
        failures: list[dict[str, Any]] = []
        try:
            failures = self.database.logs.listar(
                filters={}, order_by="ErrorDateTime", descending=True, limit=100
            )
        except Exception:
            pass
        by_day: dict[str, int] = {}
        for item in failures:
            value = item.get("ErrorDateTime")
            key = value.strftime("%d/%m") if hasattr(value, "strftime") else "Sem data"
            by_day[key] = by_day.get(key, 0) + 1
        return {**accuracy, "falhas_por_dia": by_day, "logs": failures}

    def close(self) -> None:
        self.database.dispose()
