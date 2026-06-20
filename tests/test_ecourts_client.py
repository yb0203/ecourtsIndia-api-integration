import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("ECOURTS_API_KEY", "test-key")


def make_mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    return mock


SAMPLE_CASE = {
    "data": {
        "courtCaseData": {
            "courtName": "High Court of Delhi, Delhi",
            "state": "DL",
            "petitioners": ["NTPC"],
            "respondents": ["MBECL"],
            "judges": ["Hon. Justice ABC"],
            "filingDate": "2025-01-15",
            "nextHearingDate": "2026-07-10",
            "caseStatus": "PENDING",
            "cnrCourtCode": "DLHC01",
            "caseType": "OMP_COMM",
            "cnrCaseNumber": "422",
            "historyOfCaseHearings": [
                {"hearingDate": "2026-05-01", "purposeOfListing": "Arguments", "businessOnDate": "2026-05-01"}
            ],
            "judgmentOrders": [
                {"orderDate": "2026-04-01", "orderUrl": "order.pdf"}
            ],
        }
    }
}


def test_get_case_by_cnr_returns_detail():
    mock_resp = make_mock_response(SAMPLE_CASE)
    with patch("lib.ecourts_client.requests.get", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        result = client.get_case_by_cnr("DLHC010004222025")

    assert result is not None
    assert result.court_name == "High Court of Delhi, Delhi"
    assert result.petitioner == "NTPC"
    assert result.next_hearing_date == "2026-07-10"
    assert result.cnr == "DLHC010004222025"
    assert len(result.hearings) == 1
    assert len(result.orders) == 1


def test_get_case_by_cnr_returns_none_on_404():
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.json.return_value = {"error": {"code": "CASE_NOT_FOUND"}}
    with patch("lib.ecourts_client.requests.get", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        result = client.get_case_by_cnr("XXXX999999992025")

    assert result is None


def test_search_case_constructs_cnr_and_fetches():
    mock_resp = make_mock_response(SAMPLE_CASE)
    with patch("lib.ecourts_client.requests.get", return_value=mock_resp) as mock_get:
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        result = client.search_case("DLHC01", "OMP_COMM", "422", 2025)

    # Should have called /case/DLHC010004222025
    called_url = mock_get.call_args[0][0]
    assert "DLHC010004222025" in called_url
    assert result is not None
    assert result.petitioner == "NTPC"


def test_build_cnr_format():
    from lib.ecourts_client import build_cnr
    assert build_cnr("DLHC01", "422", 2025) == "DLHC010004222025"
    assert build_cnr("WBHC01", "962", 2024) == "WBHC010009622024"
    assert build_cnr("APHC01", "1263", 2021) == "APHC010012632021"


def test_get_case_by_cnr_returns_none_when_empty_data():
    mock_resp = make_mock_response({"data": {"courtCaseData": {}}})
    with patch("lib.ecourts_client.requests.get", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        result = client.get_case_by_cnr("DLHC010004222025")

    assert result is None
