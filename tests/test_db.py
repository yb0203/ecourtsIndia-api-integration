import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_client():
    mock = MagicMock()
    with patch("lib.db.get_client", return_value=mock):
        with patch("lib.db.get_user_id", return_value="user-123"):
            yield mock


def test_get_all_cases_queries_by_user_id(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value \
        .order.return_value.execute.return_value.data = [{"id": "c1"}]

    from lib.db import get_all_cases
    result = get_all_cases()

    mock_client.table.assert_called_with("cases")
    assert result == [{"id": "c1"}]


def test_save_case_injects_user_id(mock_client):
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "c1", "user_id": "user-123", "court_code": "DEL001"}
    ]

    from lib.db import save_case
    result = save_case({"court_code": "DEL001"})

    call_args = mock_client.table.return_value.insert.call_args[0][0]
    assert call_args["user_id"] == "user-123"
    assert call_args["court_code"] == "DEL001"
    assert result["id"] == "c1"


def test_get_orders_for_case_queries_by_case_id(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value \
        .order.return_value.execute.return_value.data = []

    from lib.db import get_orders_for_case
    get_orders_for_case("case-123")

    mock_client.table.assert_called_with("orders")


def test_get_hearing_history_queries_by_case_id(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value \
        .order.return_value.execute.return_value.data = []

    from lib.db import get_hearing_history_for_case
    get_hearing_history_for_case("case-123")

    mock_client.table.assert_called_with("hearing_history")
