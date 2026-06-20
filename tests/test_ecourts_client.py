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
        "data": {
            "results": [{
                "courtName": "Delhi High Court",
                "stateCode": "DL",
                "petitioners": ["NTPC"],
                "respondents": ["MBECL"],
                "judges": ["Hon. Justice ABC"],
                "filingDate": "2025-01-15",
                "nextHearingDate": "2026-07-10",
                "caseStatus": "PENDING",
                "courtCode": "DEL001",
                "caseType": "OMP_COMM",
                "cnr": "DLHC010004222025",
            }]
        }
    })
    with patch("lib.ecourts_client.requests.get", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        result = client.search_case("DEL001", "OMP_COMM", "422", 2025)

    assert result is not None
    assert result.court_name == "Delhi High Court"
    assert result.petitioner == "NTPC"
    assert result.next_hearing_date == "2026-07-10"
    assert result.cnr == "DLHC010004222025"


def test_search_case_returns_none_when_no_results():
    mock_resp = make_mock_response({"data": {"results": []}})
    with patch("lib.ecourts_client.requests.get", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        result = client.search_case("DEL001", "OMP_COMM", "999", 2025)

    assert result is None


def test_get_orders_returns_list():
    mock_resp = make_mock_response({
        "data": {
            "orders": [
                {"orderDate": "2026-04-15", "orderNumber": "042", "pdfUrl": "https://example.com/order.pdf"},
                {"orderDate": "2026-02-10", "orderNumber": "031", "pdfUrl": "https://example.com/order2.pdf"},
            ]
        }
    })
    with patch("lib.ecourts_client.requests.get", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        orders = client.get_orders("DLHC010004222025")

    assert len(orders) == 2
    assert orders[0].order_number == "042"
    assert orders[0].pdf_url == "https://example.com/order.pdf"


def test_get_orders_returns_empty_list_when_none():
    mock_resp = make_mock_response({"data": {"orders": []}})
    with patch("lib.ecourts_client.requests.get", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        orders = client.get_orders("DLHC010004222025")

    assert orders == []


def test_refresh_case_returns_updated_data():
    mock_resp = make_mock_response({
        "data": {
            "nextHearingDate": "2026-08-01",
            "caseStatus": "PENDING",
        }
    })
    with patch("lib.ecourts_client.requests.post", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        result = client.refresh_case("DEL001", "OMP_COMM", "422", 2025)

    assert result["next_hearing_date"] == "2026-08-01"
