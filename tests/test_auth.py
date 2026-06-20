import pytest
from unittest.mock import MagicMock, patch


def test_is_authenticated_returns_false_with_no_session():
    with patch.dict("streamlit.session_state", {}, clear=True):
        from lib.auth import is_authenticated
        assert is_authenticated() is False


def test_is_authenticated_returns_true_with_session():
    mock_session = MagicMock()
    with patch.dict("streamlit.session_state", {"session": mock_session}):
        from lib.auth import is_authenticated
        assert is_authenticated() is True


def test_get_user_id_returns_none_without_session():
    with patch.dict("streamlit.session_state", {}, clear=True):
        from lib.auth import get_user_id
        assert get_user_id() is None


def test_get_user_id_returns_id_with_session():
    mock_session = MagicMock()
    mock_session.user.id = "user-123"
    with patch.dict("streamlit.session_state", {"session": mock_session}):
        from lib.auth import get_user_id
        assert get_user_id() == "user-123"
