import pytest
from unittest.mock import patch, MagicMock
import os


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("ECOURTS_API_KEY", "test-key")


def make_mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    return mock


def test_search_case_returns_result():
    mock_resp = make_mock_response({
        "results": [{
            "court_name": "Delhi High Court",
            "state": "Delhi",
            "petitioner": "NTPC",
            "respondent": "MBECL",
            "judge": "Hon. Justice ABC",
            "filing_date": "2025-01-15",
            "next_hearing_date": "2026-07-10",
            "status": "Pending",
        }]
    })
    with patch("lib.ecourts_client.requests.get", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        result = client.search_case("DEL001", "OMP(COMM)", "422", 2025)

    assert result is not None
    assert result.court_name == "Delhi High Court"
    assert result.petitioner == "NTPC"
    assert result.next_hearing_date == "2026-07-10"


def test_search_case_returns_none_when_no_results():
    mock_resp = make_mock_response({"results": []})
    with patch("lib.ecourts_client.requests.get", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        result = client.search_case("DEL001", "OMP(COMM)", "999", 2025)

    assert result is None


def test_get_orders_returns_list():
    mock_resp = make_mock_response({
        "orders": [
            {"date": "2026-04-15", "number": "042", "pdf_url": "https://example.com/order.pdf"},
            {"date": "2026-02-10", "number": "031", "pdf_url": "https://example.com/order2.pdf"},
        ]
    })
    with patch("lib.ecourts_client.requests.get", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        orders = client.get_orders("DEL001", "OMP(COMM)", "422", 2025)

    assert len(orders) == 2
    assert orders[0].order_number == "042"
    assert orders[0].pdf_url == "https://example.com/order.pdf"


def test_get_orders_returns_empty_list_when_none():
    mock_resp = make_mock_response({"orders": []})
    with patch("lib.ecourts_client.requests.get", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        orders = client.get_orders("DEL001", "OMP(COMM)", "422", 2025)

    assert orders == []


def test_refresh_case_returns_updated_data():
    mock_resp = make_mock_response({
        "next_hearing_date": "2026-08-01",
        "status": "Pending",
    })
    with patch("lib.ecourts_client.requests.post", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        result = client.refresh_case("DEL001", "OMP(COMM)", "422", 2025)

    assert result["next_hearing_date"] == "2026-08-01"
