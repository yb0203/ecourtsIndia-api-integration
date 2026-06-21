import pytest
from unittest.mock import MagicMock, patch


def _session(token):
    s = MagicMock()
    s.access_token = token
    return s


def _live_auth_header(client):
    """The Authorization header the PostgREST HTTP session actually sends."""
    return client.postgrest.session.headers.get("Authorization")


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://dummy.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-xyz")


def test_user_jwt_is_applied_to_live_postgrest_session():
    """A signed-in user's JWT must reach the real HTTP session, or RLS fails."""
    with patch.dict("streamlit.session_state", {"session": _session("USER-JWT")}, clear=True):
        from lib.supabase_client import get_client
        client = get_client()
        assert _live_auth_header(client) == "Bearer USER-JWT"


def test_anon_key_used_without_session():
    with patch.dict("streamlit.session_state", {}, clear=True):
        from lib.supabase_client import get_client
        client = get_client()
        assert _live_auth_header(client) == "Bearer anon-xyz"


def test_cached_per_session():
    with patch.dict("streamlit.session_state", {"session": _session("USER-JWT")}, clear=True):
        from lib.supabase_client import get_client
        assert get_client() is get_client()  # same Client reused within a session


def test_sessions_are_isolated_no_global_singleton():
    """Two different sessions must get independent clients (no cross-tenant bleed)."""
    from lib.supabase_client import get_client
    with patch.dict("streamlit.session_state", {"session": _session("JWT-A")}, clear=True):
        client_a = get_client()
        header_a = _live_auth_header(client_a)
    with patch.dict("streamlit.session_state", {"session": _session("JWT-B")}, clear=True):
        client_b = get_client()
        header_b = _live_auth_header(client_b)
    assert client_a is not client_b
    assert header_a == "Bearer JWT-A"
    assert header_b == "Bearer JWT-B"


def test_token_reapplied_when_session_appears():
    """An anon client that later gets a session must switch to the user JWT."""
    import streamlit as st
    with patch.dict("streamlit.session_state", {}, clear=True):
        from lib.supabase_client import get_client
        anon_client = get_client()
        assert _live_auth_header(anon_client) == "Bearer anon-xyz"
        # simulate login within the same session (mutate the real state proxy)
        st.session_state["session"] = _session("USER-JWT")
        client = get_client()
        assert _live_auth_header(client) == "Bearer USER-JWT"
