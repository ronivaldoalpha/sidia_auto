from datetime import datetime, timedelta

from services.dashboard_metrics import build_dashboard_metrics


def test_dashboard_metrics_builds_success_failure_and_server_breakdown():
    start = datetime(2026, 1, 1)
    result = build_dashboard_metrics(
        [
            {"TrDateTime": start + timedelta(hours=1), "Cam1Server": "DF-01", "TrController": "A"},
            {"TrDateTime": start + timedelta(days=1, hours=1), "Cam1Server": "DF-01", "TrController": "A"},
        ],
        [
            {"ErrorDateTime": start + timedelta(days=1, hours=2), "TargetURL": "DF-01", "TrController": "A", "ErrorMessage": "timeout"},
        ],
        start=start,
        end=start + timedelta(days=2),
    )
    assert result["total"] == 3
    assert result["sucessos"] == 2
    assert result["falhas"] == 1
    assert result["acuracidade"] == 66.67
    assert result["servidores"][0]["falhas"] == 1
    assert len(result["rows"]) == 3
    assert len(result["dias"]) == 2
