import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from services.PyVaultsiteDB import Vault, log_requests


def test_log_table_name_is_used_by_schema_and_dependency_check():
    assert log_requests.name == "LogRequestsTransaction"
    assert "LogRequestsTransaction" in Vault.tabelas_dependentes(object.__new__(Vault))


def test_log_table_model_matches_production_request_columns():
    assert set(log_requests.c.keys()) == {
        "Id",
        "RequestDateTime",
        "TrController",
        "TargetServerIP",
        "TargetURL",
        "RequestStatus",
        "ErrorMessage",
        "PayloadMessage",
    }
    assert log_requests.c.RequestDateTime.server_default is not None
