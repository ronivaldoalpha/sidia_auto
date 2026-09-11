"""Transformações puras para os indicadores da Dashboard."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Iterable


def _as_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return None


def _server(row: dict[str, Any], *, failure: bool = False) -> str:
    if failure:
        return str(row.get("ServerName") or row.get("TargetURL") or "Não identificado")[:80]
    return str(row.get("Cam1Server") or row.get("ServerName") or "Não identificado")


def build_dashboard_metrics(
    transactions: Iterable[dict[str, Any]],
    failures: Iterable[dict[str, Any]],
    *,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    """Gera métricas serializáveis, sem depender de Flet ou SQLAlchemy."""
    success_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    for source in transactions:
        value = _as_datetime(source.get("TrDateTime"))
        if value is None or not (start <= value < end):
            continue
        success_rows.append({
            "DataHora": value, "Status": "Sucesso", "Servidor": _server(source),
            "Controladora": source.get("TrController") or "—",
            "Mensagem": source.get("TrName") or source.get("Transaction") or "Evento processado",
        })
    for source in failures:
        value = _as_datetime(source.get("ErrorDateTime"))
        if value is None or not (start <= value < end):
            continue
        failure_rows.append({
            "DataHora": value, "Status": "Falha", "Servidor": _server(source, failure=True),
            "Controladora": source.get("TrController") or "—",
            "Mensagem": source.get("ErrorMessage") or "Falha sem mensagem",
        })

    by_day: dict[date, dict[str, int]] = defaultdict(lambda: {"sucessos": 0, "falhas": 0})
    by_server: dict[str, dict[str, int]] = defaultdict(lambda: {"sucessos": 0, "falhas": 0})
    for row in success_rows:
        day = row["DataHora"].date()
        by_day[day]["sucessos"] += 1
        by_server[row["Servidor"]]["sucessos"] += 1
    for row in failure_rows:
        day = row["DataHora"].date()
        by_day[day]["falhas"] += 1
        by_server[row["Servidor"]]["falhas"] += 1

    days: list[dict[str, Any]] = []
    cursor = start.date()
    last = (end - timedelta(microseconds=1)).date()
    while cursor <= last:
        item = by_day[cursor]
        days.append({"data": cursor, "sucessos": item["sucessos"], "falhas": item["falhas"]})
        cursor += timedelta(days=1)

    servers: list[dict[str, Any]] = []
    for name in sorted(by_server, key=str.casefold):
        item = by_server[name]
        total = item["sucessos"] + item["falhas"]
        servers.append({"servidor": name, "sucessos": item["sucessos"], "falhas": item["falhas"], "acuracidade": round(item["sucessos"] * 100 / total, 2) if total else 0.0})

    rows = sorted(success_rows + failure_rows, key=lambda row: row["DataHora"], reverse=True)
    total_success = len(success_rows)
    total_failure = len(failure_rows)
    total = total_success + total_failure
    return {
        "inicio": start, "fim": end, "total": total, "sucessos": total_success, "falhas": total_failure,
        "acuracidade": round(total_success * 100 / total, 2) if total else 0.0,
        "dias": days, "servidores": servers, "rows": rows,
    }
