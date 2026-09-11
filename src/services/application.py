from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .PyVaultsiteDB import Vault
    from .pydigifort import Servidor


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
        from .pydigifort import AuthConfig, Servidor
        auth = AuthConfig(self.username, self.password, self.auth_mode) if self.username else None
        return Servidor(self.hostname, self.port, auth)


@dataclass
class ServiceHealth:
    name: str
    kind: str
    online: bool | None
    detail: str
    checked_at: datetime | None = None
    credential_error: bool = False

    @property
    def label(self) -> str:
        if self.credential_error:
            return "CREDENCIAL"
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
    dashboard_start: datetime | None = None
    dashboard_end: datetime | None = None


class ApplicationService:
    """Orquestra banco, Digifort e dados temporários da UI."""

    def __init__(self) -> None:
        self.state = AppState()
        from .PyVaultsiteDB import Vault
        from utils.secrets import load_database_secret
        secret = load_database_secret()
        self.database = Vault(**secret.vault_kwargs())
        try:
            self.database.criar_tabela_configuracoes()
            self._load_digifort_configs()
        except Exception as exc:
            # A UI pode iniciar off-line; a configuração será carregada quando
            # o banco estiver disponível e o health check for executado.
            from .error_handling import log_error
            log_error("inicializar configurações do sistema", exc)
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

    def add_digifort(self, config: DigifortConfig) -> tuple[bool, str]:
        try:
            self._persist_digifort(config)
            self.state.digifort.append(config)
            return True, f"Servidor {config.name} salvo."
        except Exception as exc:
            from .error_handling import log_error
            info = log_error("salvar servidor Digifort", exc, context={"server": config.name, "host": config.hostname})
            return False, info.user_message

    def update_digifort(self, original_name: str, config: DigifortConfig) -> tuple[bool, str]:
        for index, current in enumerate(self.state.digifort):
            if current.name == original_name:
                try:
                    self._persist_digifort(config, original_name=original_name)
                    self.state.digifort[index] = config
                    self.state.health.pop(original_name, None)
                    return True, f"Servidor {config.name} atualizado."
                except Exception as exc:
                    from .error_handling import log_error
                    info = log_error("editar servidor Digifort", exc, context={"server": original_name, "host": config.hostname})
                    return False, info.user_message
        return False, "Servidor Digifort não encontrado."

    def remove_digifort(self, name: str) -> tuple[bool, str]:
        before = len(self.state.digifort)
        try:
            self.database.system_settings.excluir({"ServiceType": "DIGIFORT", "ServiceName": name})
            self.state.digifort = [item for item in self.state.digifort if item.name != name]
            self.state.health.pop(name, None)
            return len(self.state.digifort) < before, f"Servidor {name} excluído."
        except Exception as exc:
            from .error_handling import log_error
            info = log_error("excluir servidor Digifort", exc, context={"server": name})
            return False, info.user_message

    def _load_digifort_configs(self) -> None:
        rows = self.database.system_settings.listar(filters={"ServiceType": "DIGIFORT"}, order_by="ServiceName")
        self.state.digifort = [DigifortConfig(
            name=str(row.get("ServiceName") or ""), hostname=str(row.get("Hostname") or ""),
            port=int(row.get("Port") or 8601), username=str(row.get("Username") or ""),
            password=str(row.get("Password") or ""), auth_mode=str(row.get("AuthMode") or "safe"),
            enabled=bool(row.get("Enabled", True)),
        ) for row in rows if row.get("ServiceName") and row.get("Hostname")]

    def _persist_digifort(self, config: DigifortConfig, *, original_name: str | None = None) -> None:
        values = {
            "ServiceType": "DIGIFORT", "ServiceName": config.name, "Hostname": config.hostname,
            "Port": config.port, "Username": config.username, "Password": config.password,
            "AuthMode": config.auth_mode, "Enabled": config.enabled, "UpdatedAt": datetime.now(),
        }
        filters = {"ServiceType": "DIGIFORT", "ServiceName": original_name or config.name}
        current = self.database.system_settings.obter(**filters)
        if current:
            self.database.system_settings.atualizar({"Id": current["Id"]}, values)
        else:
            values["CreatedAt"] = datetime.now()
            self.database.system_settings.criar(**values)

    def save_database_settings(self, *, hostname: str, database: str, driver: str,
                               auth_mode: str, username: str = "", password: str = "") -> tuple[bool, str]:
        """Salva a conexão no .env e troca o engine sem expor a senha na UI."""
        try:
            from utils.secrets import DatabaseSecret, save_database_secret
            if auth_mode == "windows":
                username, password = "", ""
            elif not password and getattr(self.database, "auth", None) and username == self.database.auth[0]:
                password = self.database.auth[1]
            secret = DatabaseSecret(hostname=hostname.strip(), database=database.strip(), driver=driver.strip(), username=username.strip(), password=password)
            if not secret.hostname or not secret.database or not secret.driver:
                raise ValueError("Servidor, banco e driver são obrigatórios.")
            save_database_secret(secret)
            from .PyVaultsiteDB import Vault
            old_database = self.database
            self.database = Vault(**secret.vault_kwargs())
            old_database.dispose()
            return True, "Configuração do banco salva. Use Verificar conexão para validar o acesso."
        except Exception as exc:
            from .error_handling import log_error
            info = log_error("salvar configuração do banco", exc, context={"hostname": hostname, "database": database, "auth_mode": auth_mode})
            return False, info.user_message

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
            from .error_handling import log_error
            info = log_error("salvar vínculo porta-câmera", exc, context={"tag": tag, "camera": camera})
            return False, info.user_message

    def check_database(self) -> ServiceHealth:
        try:
            self.database.testar_servidor()
            self.database.testar_conexao()
            missing = self.database.verificar_tabelas_dependentes()
            if missing:
                detail = "Servidor e banco conectados, mas faltam tabelas: " + ", ".join(missing)
                health = ServiceHealth("Banco Vault Site", "database", False, detail, datetime.now())
            else:
                health = ServiceHealth("Banco Vault Site", "database", True, "SQL Server, banco DataDBEnt e tabelas dependentes disponíveis", datetime.now())
        except Exception as exc:
            from .error_handling import log_error
            info = log_error("verificar conexão com banco de dados", exc)
            health = ServiceHealth("Banco Vault Site", "database", False, info.user_message, datetime.now(), info.is_credential)
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
            detail = str(exc)
            credential_error = any(token in detail.casefold() for token in ("401", "403", "auth", "credential", "senha", "usuário"))
            from .error_handling import log_error
            info = log_error("verificar conexão Digifort", exc, context={"server": config.name, "host": config.hostname})
            health = ServiceHealth(config.name, "digifort", False, info.detail, datetime.now(), credential_error or info.is_credential)
        self.state.health[config.name] = health
        return health

    def check_all(self) -> list[ServiceHealth]:
        result = [self.check_database()]
        result.extend(self.check_digifort(item) for item in self.state.digifort if item.enabled)
        return result

    def metrics(self, start: datetime | None = None, end: datetime | None = None) -> dict[str, Any]:
        end = end or datetime.now()
        start = start or (end - timedelta(days=30))
        transactions: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        try:
            transactions = self.database.transacoes_com_mapeamento(inicio=start, fim=end, limit=10000)
        except Exception:
            pass
        try:
            failures = self.database.logs.listar(order_by="ErrorDateTime", descending=True, limit=10000)
        except Exception:
            pass
        from .dashboard_metrics import build_dashboard_metrics
        return build_dashboard_metrics(transactions, failures, start=start, end=end)

    def close(self) -> None:
        self.database.dispose()
