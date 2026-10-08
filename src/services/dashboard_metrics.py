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


def _server(row: dict[str, Any]) -> str:
    return str(row.get("TargetServerIP") or "Não identificado")[:80]


def build_dashboard_metrics(
    requests: Iterable[dict[str, Any]],
    *,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    """Gera métricas serializáveis, sem depender de Flet ou SQLAlchemy."""
    rows: list[dict[str, Any]] = []
    by_day: dict[date, dict[str, int]] = defaultdict(lambda: {"sucessos": 0, "falhas": 0})
    by_server: dict[str, dict[str, int]] = defaultdict(lambda: {"sucessos": 0, "falhas": 0})
    for source in requests:
        value = _as_datetime(source.get("RequestDateTime"))
        if value is None or not (start <= value < end):
            continue
        status = str(source.get("RequestStatus") or "").strip()
        outcome = status.casefold()
        if outcome not in {"sucesso", "falha"}:
            continue
        server = _server(source)
        rows.append({
            "DataHora": value, "Status": "Sucesso" if outcome == "sucesso" else "Falha",
            "Servidor": server,
            "Controladora": source.get("TrController") or "—",
            "Mensagem": source.get("ErrorMessage") or source.get("PayloadMessage") or "Requisição processada",
        })
        day_counts = by_day[value.date()]
        server_counts = by_server[server]
        if outcome == "sucesso":
            day_counts["sucessos"] += 1
            server_counts["sucessos"] += 1
        else:
            day_counts["falhas"] += 1
            server_counts["falhas"] += 1

    days: list[dict[str, Any]] = []
    cursor = start.date()
    last = (end - timedelta(microseconds=1)).date()
    while cursor <= last:
        item = by_day[cursor]
        days.append({"data": cursor, "sucessos": item["sucessos"], "falhas": item["falhas"]})
        cursor += timedelta(days=1)

    servers: list[dict[str, Any]] = []
    for name, item in sorted(by_server.items(), key=lambda pair: pair[0].casefold()):
        total = item["sucessos"] + item["falhas"]
        servers.append({
            "servidor": name,
            "sucessos": item["sucessos"],
            "falhas": item["falhas"],
            "acuracidade": round(item["sucessos"] * 100 / total, 2) if total else 0.0,
        })

    rows.sort(key=lambda row: row["DataHora"], reverse=True)
    total_success = sum(item["sucessos"] for item in by_day.values())
    total_failure = sum(item["falhas"] for item in by_day.values())
    total = total_success + total_failure
    return {
        "inicio": start, "fim": end, "total": total, "sucessos": total_success, "falhas": total_failure,
        "acuracidade": round(total_success * 100 / total, 2) if total else 0.0,
        "dias": days, "servidores": servers, "rows": rows,
    }
