import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.exc import ProgrammingError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from interfaces.views import _load_dashboard_metrics


class MissingLogTableService:
    def metrics(self, *, start: datetime, end: datetime) -> dict:
        raise ProgrammingError(
            "SELECT * FROM dbo.LogRequestsTransaction",
            {},
            Exception("[42S02] Invalid object name 'dbo.LogRequestsTransaction'."),
        )


def test_dashboard_query_failure_returns_empty_metrics_and_logs_error(tmp_path, monkeypatch):
    from services import error_handling

    monkeypatch.setattr(error_handling, "_LOG_PATH", tmp_path / "application.log")
    start = datetime(2026, 1, 1)
    metrics, message = _load_dashboard_metrics(
        MissingLogTableService(),
        start=start,
        end=start + timedelta(days=1),
        operation="consultar indicadores da dashboard",
    )

    assert metrics["total"] == 0
    assert metrics["rows"] == []
    assert message == "A consulta não pôde ser concluída porque um objeto necessário não foi encontrado no banco configurado."
    log_content = (tmp_path / "application.log").read_text(encoding="utf-8")
    assert "dbo.LogRequestsTransaction" in log_content
