"""Acesso ao banco Microsoft SQL Server do Vault Site com SQLAlchemy 2.0.

Exemplo::

    from PyVaultsiteDB import Vault

    db = Vault(hostname=r"localhost\\sqlexpress")
    mappings = db.mapeamentos.listar()
    db.mapeamentos.criar(
        UnitNo="01", TrController="AC-TER-08",
        Cam1Nome="CAM-TER-02", Cam1Server="172.16.0.151",
        dig_alerta=True,
    )

Por padrão é usada autenticação integrada do Windows (Trusted Connection).
Para autenticação SQL Server, informe ``auth=("usuario", "senha")``.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator, Mapping, Sequence
from urllib.parse import quote_plus

try:
    from sqlalchemy import (
        Boolean, Column, DateTime, Integer, MetaData, String, Table, Unicode,
        Uuid,
        and_, create_engine, delete, func, inspect, insert, select, text, update,
    )
    from sqlalchemy.engine import Engine, URL
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.orm import Session, sessionmaker
except ImportError as exc:  # pragma: no cover - mensagem útil em instalação incompleta
    raise ImportError(
        "PyVaultsiteDB requer SQLAlchemy 2.x e pyodbc. "
        "Instale com: pip install 'SQLAlchemy>=2.0,<3' pyodbc"
    ) from exc

__all__ = ["Vault", "VaultDBError", "VaultValidationError"]


class VaultDBError(RuntimeError):
    """Erro de conexão ou operação no banco Vault Site."""


class VaultValidationError(ValueError):
    """Entrada inválida ou coluna/tabela não permitida."""


metadata = MetaData()

# Os nomes físicos são preservados exatamente como documentados.
tbl_transaction = Table(
    "tblTransaction", metadata,
    Column("TrDateTime", DateTime), Column("CardNo", String(16)),
    Column("TrCardID", String(100)), Column("UnitNo", String(4)),
    Column("Transaction", Unicode(50)), Column("TrCode", String(2)),
    Column("TrController", Unicode(30)), Column("TrName", Unicode(50)),
    schema="dbo",
)

controller = Table(
    "Controller", metadata,
    Column("Controller_RecID", Uuid, primary_key=True),
    Column("TagName", Unicode(30), nullable=False), Column("SiteCode", String(50)),
    Column("Workstation", Unicode(50), nullable=False), Column("UnitNo", String(4)),
    Column("Desc", Unicode(50)), Column("OpenTime", Integer, nullable=False),
    Column("ReleaseTime", Integer, nullable=False), Column("RelTZ", Integer, nullable=False),
    Column("CardPinInTZ", Integer, nullable=False), Column("CardPinOutTZ", Integer, nullable=False),
    Column("UnitPinNo", String(40)), Column("UnitPinNoTZ", String(20)),
    Column("AutoPin", Boolean, nullable=False), Column("CardPinMode", Boolean, nullable=False),
    Column("CardLockOut", Boolean, nullable=False), Column("Buzzer", Boolean, nullable=False),
    Column("PushButtonTZ", Integer, nullable=False), Column("AntiPBTZ", Integer, nullable=False),
    Column("EntryCam", String(50)), Column("ExitCam", String(50)),
    Column("EntryCam1", String(50)), Column("ExitCam1", String(50)),
    Column("EntryCam2", String(50)), Column("ExitCam2", String(50)),
    Column("ControllerType", Unicode(50)), Column("ReportMode", Boolean),
    Column("GTMode", Boolean), Column("IOMode", Boolean), Column("RCMode", Boolean),
    Column("AlarmMode", String(50)), Column("LiftMode", String(50)), Column("Status", Boolean),
    *[Column(f"Controller_{i:02d}", String(100)) for i in range(1, 26)],
    Column("DualCardMode", Boolean), Column("DualCardInTZ", Integer),
    Column("DualCardOutTZ", Integer), Column("RackOutputControl", Integer),
    Column("RackID", Integer), Column("LastTrCode", String(2)),
    Column("InterlockingMode", Boolean, nullable=False), Column("CarParkCounterMode", Boolean, nullable=False),
    Column("CarParkGroupID", Unicode(3), nullable=False), Column("PersonCounterMode", Boolean, nullable=False),
    Column("PersonCounterGroupID", Unicode(3), nullable=False),
    Column("TurnstilePernaltyMode", Boolean, nullable=False), Column("CanteenMode", Boolean, nullable=False),
    Column("FPEntry", Unicode(50)), Column("FPExit", Unicode(50)),
    Column("InBeaconMac", Unicode(30)), Column("OutBeaconMac", Unicode(30)), schema="dbo",
)

tbl_mapping = Table(
    "tblMappingControllerCam", metadata,
    Column("Id", Integer, primary_key=True), Column("UnitNo", String(4)),
    Column("TrController", Unicode(30), nullable=False), Column("Cam1Nome", Unicode(50)),
    Column("Cam1Server", String(15)), Column("Cam2Nome", Unicode(50)),
    Column("Cam2Server", String(15)), Column("dig_alerta", Boolean), schema="dbo",
)

log_requests = Table(
    "logrequeststrasaction", metadata,
    Column("Id", Integer, primary_key=True), Column("ErrorDateTime", DateTime),
    Column("TrController", Unicode(30)), Column("TargetURL", String(1000)),
    Column("ErrorMessage", Unicode(4000)), Column("PayloadMessage", String(500)),
    schema="dbo",
)

eventos_integracao = Table(
    "T_INTEGRACAO_EVENTOS", metadata,
    Column("Data", DateTime), Column("NomeSite", Unicode(100)),
    Column("Controladora", Unicode(30)), Column("NrCartao", String(100)),
    Column("TrCodigo", String(2)), Column("TrDescricao", Unicode(50)),
    Column("TrNome", Unicode(50)), schema="dbo",
)

system_settings = Table(
    "SystemSettings", metadata,
    Column("Id", Integer, primary_key=True),
    Column("ServiceType", Unicode(30), nullable=False),
    Column("ServiceName", Unicode(100), nullable=False),
    Column("Hostname", Unicode(255)), Column("Port", Integer),
    Column("DatabaseName", Unicode(128)), Column("Username", Unicode(255)),
    Column("Password", Unicode(1024)), Column("AuthMode", Unicode(30)),
    Column("Enabled", Boolean, nullable=False),
    Column("CreatedAt", DateTime), Column("UpdatedAt", DateTime),
    schema="dbo",
)

TABLES = {
    "transactions": tbl_transaction,
    "controllers": controller,
    "mappings": tbl_mapping,
    "logs": log_requests,
    "audit_events": eventos_integracao,
    "system_settings": system_settings,
}


class _TableGateway:
    """CRUD seguro para uma tabela conhecida do esquema."""

    def __init__(self, vault: "Vault", table: Table):
        self.vault, self.table = vault, table

    def _values(self, values: Mapping[str, Any]) -> dict[str, Any]:
        allowed = set(self.table.c.keys())
        unknown = set(values) - allowed
        if unknown:
            raise VaultValidationError(f"Colunas inválidas para {self.table.name}: {sorted(unknown)}")
        return dict(values)

    def _where(self, filters: Mapping[str, Any]):
        values = self._values(filters)
        return and_(*(self.table.c[k] == v for k, v in values.items())) if values else None

    def listar(self, *, filters: Mapping[str, Any] | None = None,
               limit: int | None = None, order_by: str | None = None,
               descending: bool = False) -> list[dict[str, Any]]:
        statement = select(self.table)
        where = self._where(filters or {})
        if where is not None:
            statement = statement.where(where)
        if order_by:
            if order_by not in self.table.c:
                raise VaultValidationError(f"Coluna de ordenação inválida: {order_by}")
            column = self.table.c[order_by]
            statement = statement.order_by(column.desc() if descending else column.asc())
        if limit is not None:
            if limit < 1:
                raise VaultValidationError("limit deve ser maior que zero")
            statement = statement.limit(limit)
        with self.vault.session() as session:
            return [dict(row) for row in session.execute(statement).mappings().all()]

    def obter(self, **filters: Any) -> dict[str, Any] | None:
        rows = self.listar(filters=filters, limit=1)
        return rows[0] if rows else None

    def criar(self, **values: Any) -> dict[str, Any] | None:
        values = self._values(values)
        if not values:
            raise VaultValidationError("Informe ao menos uma coluna")
        with self.vault.session() as session:
            result = session.execute(insert(self.table).values(**values))
            session.commit()
            if result.inserted_primary_key:
                return self.obter(Id=result.inserted_primary_key[0])
        return None

    def atualizar(self, filters: Mapping[str, Any], values: Mapping[str, Any]) -> int:
        values = self._values(values)
        where = self._where(filters)
        if where is None:
            raise VaultValidationError("Atualização exige filtros; não é permitido atualizar tudo")
        if not values:
            raise VaultValidationError("Informe valores para atualizar")
        with self.vault.session() as session:
            result = session.execute(update(self.table).where(where).values(**values))
            session.commit()
            return int(result.rowcount or 0)

    def excluir(self, filters: Mapping[str, Any]) -> int:
        where = self._where(filters)
        if where is None:
            raise VaultValidationError("Exclusão exige filtros; não é permitido excluir tudo")
        with self.vault.session() as session:
            result = session.execute(delete(self.table).where(where))
            session.commit()
            return int(result.rowcount or 0)


class Vault:
    """Gateway do banco ``DataDBEnt`` do Vault Site.

    Args:
        hostname: Servidor SQL Server, por exemplo ``r"localhost\\sqlexpress"``.
        auth: ``None`` para Windows Integrated Security ou ``(user, password)``.
        database: Nome do banco, por padrão ``DataDBEnt``.
        driver: Driver ODBC instalado no Windows/Linux.
        echo: Ativa logging SQL do SQLAlchemy.
        connect_args: Argumentos extras passados ao pyodbc.
    """

    def __init__(self, hostname: str = r"localhost\sqlexpress",
                 auth: tuple[str, str] | None = None, *, database: str = "DataDBEnt",
                 driver: str = "ODBC Driver 18 for SQL Server", echo: bool = False,
                 connect_args: Mapping[str, Any] | None = None, **engine_options: Any) -> None:
        if not hostname or not database:
            raise VaultValidationError("hostname e database são obrigatórios")
        if auth is not None and (not isinstance(auth, (tuple, list)) or len(auth) != 2):
            raise VaultValidationError("auth deve ser None ou uma tupla (usuario, senha)")
        self.hostname, self.database, self.driver, self.auth = hostname, database, driver, auth
        self.connect_args = dict(connect_args or {})
        query = {"driver": driver}
        if auth is None:
            query["trusted_connection"] = "yes"
            query["TrustServerCertificate"] = "yes"
        else:
            query["TrustServerCertificate"] = "yes"
        url = URL.create("mssql+pyodbc", username=None if auth is None else str(auth[0]),
                         password=None if auth is None else str(auth[1]), host=hostname,
                         database=database, query=query)
        options = {"pool_pre_ping": True, "future": True, "echo": echo}
        options.update(engine_options)
        try:
            self.engine: Engine = create_engine(url, connect_args=self.connect_args, **options)
            self.Session = sessionmaker(bind=self.engine, future=True, expire_on_commit=False)
        except SQLAlchemyError as exc:
            raise VaultDBError(f"Não foi possível configurar a conexão com {hostname}: {exc}") from exc
        self.transactions = _TableGateway(self, tbl_transaction)
        self.controllers = _TableGateway(self, controller)
        self.mapeamentos = _TableGateway(self, tbl_mapping)
        self.logs = _TableGateway(self, log_requests)
        self.eventos = _TableGateway(self, eventos_integracao)
        self.system_settings = _TableGateway(self, system_settings)
        # Aliases em inglês para facilitar integração com código existente.
        self.mapping = self.mapeamentos
        self.audit_events = self.eventos

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Fornece uma sessão transacional com rollback automático em exceções."""
        session = self.Session()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def testar_conexao(self) -> bool:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True

    def testar_servidor(self) -> bool:
        """Testa o SQL Server usando ``master``, antes de testar o banco alvo."""
        query = {"driver": self.driver, "TrustServerCertificate": "yes"}
        if self.auth is None:
            query["trusted_connection"] = "yes"
        url = URL.create(
            "mssql+pyodbc",
            username=None if self.auth is None else str(self.auth[0]),
            password=None if self.auth is None else str(self.auth[1]),
            host=self.hostname,
            database="master",
            query=query,
        )
        engine = create_engine(url, connect_args=self.connect_args, pool_pre_ping=True, future=True)
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        finally:
            engine.dispose()

    def tabelas_dependentes(self) -> list[str]:
        return ["Controller", "tblTransaction", "tblMappingControllerCam", "logrequeststrasaction", "SystemSettings"]

    def verificar_tabelas_dependentes(self) -> list[str]:
        """Retorna as tabelas dbo ausentes no banco já conectado."""
        inspector = inspect(self.engine)
        return [name for name in self.tabelas_dependentes() if not inspector.has_table(name, schema="dbo")]

    def executar(self, sql: str, params: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
        """Executa SQL parametrizado e retorna linhas, quando houver.

        Para valores, sempre use ``:nome`` e ``params``. Nomes de tabela/coluna
        não devem ser interpolados a partir de entrada do usuário.
        """
        if not sql or not sql.strip():
            raise VaultValidationError("SQL não pode ser vazio")
        with self.session() as session:
            result = session.execute(text(sql), dict(params or {}))
            rows = [dict(row) for row in result.mappings().all()] if result.returns_rows else []
            session.commit()
            return rows

    def transacoes_com_mapeamento(self, *, inicio: datetime | None = None,
                                  fim: datetime | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        """Consulta eventos de acesso e sua regra de câmeras por controladora."""
        statement = select(tbl_transaction, tbl_mapping).select_from(
            tbl_transaction.outerjoin(tbl_mapping, tbl_transaction.c.TrController == tbl_mapping.c.TrController)
        )
        filters = []
        if inicio is not None:
            filters.append(tbl_transaction.c.TrDateTime >= inicio)
        if fim is not None:
            filters.append(tbl_transaction.c.TrDateTime < fim)
        if filters:
            statement = statement.where(and_(*filters))
        statement = statement.order_by(tbl_transaction.c.TrDateTime.desc())
        if limit is not None:
            statement = statement.limit(limit)
        with self.session() as session:
            return [dict(row) for row in session.execute(statement).mappings().all()]

    def taxa_acuracidade(self, *, inicio: datetime, fim: datetime) -> dict[str, Any]:
        """Calcula eventos, falhas e percentual de acuracidade no período."""
        with self.session() as session:
            total = session.scalar(select(func.count()).select_from(tbl_transaction).where(
                and_(tbl_transaction.c.TrDateTime >= inicio, tbl_transaction.c.TrDateTime < fim))) or 0
            failures = session.scalar(select(func.count()).select_from(log_requests).where(
                and_(log_requests.c.ErrorDateTime >= inicio, log_requests.c.ErrorDateTime < fim))) or 0
        accuracy = 100.0 if not total else max(0.0, (int(total) - int(failures)) * 100.0 / int(total))
        return {"inicio": inicio, "fim": fim, "total_eventos": int(total),
                "falhas": int(failures), "taxa_acuracidade": round(accuracy, 2)}

    def executar_processador_transactions(self) -> list[dict[str, Any]]:
        """Executa a stored procedure documentada, sem concatenar parâmetros."""
        return self.executar("EXEC dbo.sp_ProcessarTransactionHTTP")

    def criar_tabelas(self) -> None:
        """Cria apenas tabelas ausentes; não altera tabelas existentes.

        Use somente em um banco de desenvolvimento. Tabelas nativas do Vault
        podem não ter todas as chaves descritas no dicionário fornecido.
        """
        metadata.create_all(self.engine, checkfirst=True)

    def criar_tabela_configuracoes(self) -> None:
        """Cria somente ``dbo.SystemSettings`` se ela ainda não existir."""
        system_settings.create(self.engine, checkfirst=True)

    def dispose(self) -> None:
        """Libera o pool de conexões."""
        self.engine.dispose()

    def __enter__(self) -> "Vault":
        return self

    def __exit__(self, *_: Any) -> None:
        self.dispose()

    def __repr__(self) -> str:
        return f"Vault(hostname={self.hostname!r}, database={self.database!r})"
