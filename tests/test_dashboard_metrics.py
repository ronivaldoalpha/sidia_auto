from datetime import datetime, timedelta

from services.dashboard_metrics import build_dashboard_metrics


def test_dashboard_metrics_counts_recorded_status_and_groups_by_target_server():
    start = datetime(2026, 1, 1)
    result = build_dashboard_metrics(
        [
            {"RequestDateTime": start + timedelta(hours=1), "TargetServerIP": "10.0.0.1", "RequestStatus": "Sucesso", "TrController": "A"},
            {"RequestDateTime": start + timedelta(days=1, hours=1), "TargetServerIP": "10.0.0.1", "RequestStatus": "Falha", "TrController": "A", "ErrorMessage": "timeout"},
            {"RequestDateTime": start + timedelta(days=1, hours=2), "TargetServerIP": "10.0.0.2", "RequestStatus": "Sucesso"},
        ],
        start=start,
        end=start + timedelta(days=2),
    )
    assert result["total"] == 3
    assert result["sucessos"] == 2
    assert result["falhas"] == 1
    assert result["acuracidade"] == 66.67
    assert result["servidores"][0] == {
        "servidor": "10.0.0.1", "sucessos": 1, "falhas": 1, "acuracidade": 50.0,
    }
    assert result["servidores"][1] == {
        "servidor": "10.0.0.2", "sucessos": 1, "falhas": 0, "acuracidade": 100.0,
    }
    assert result["dias"][0]["sucessos"] == 1
    assert result["dias"][1]["sucessos"] == 1
    assert result["dias"][1]["falhas"] == 1
    assert [row["Status"] for row in result["rows"]] == ["Sucesso", "Falha", "Sucesso"]
    assert len(result["dias"]) == 2


def test_dashboard_metrics_ignores_unknown_statuses_and_requests_outside_period():
    start = datetime(2026, 1, 1)
    result = build_dashboard_metrics(
        [
            {"RequestDateTime": start + timedelta(hours=1), "TargetServerIP": "10.0.0.1", "RequestStatus": "Sucesso"},
            {"RequestDateTime": start + timedelta(hours=2), "TargetServerIP": "10.0.0.1", "RequestStatus": "Pendente"},
            {"RequestDateTime": start + timedelta(days=1), "TargetServerIP": "10.0.0.1", "RequestStatus": "Falha"},
        ],
        start=start,
        end=start + timedelta(days=1),
    )
    assert result["total"] == 1
    assert result["sucessos"] == 1
    assert result["falhas"] == 0
    assert result["acuracidade"] == 100.0
