import pytest
from unittest.mock import MagicMock, patch


def _session(token="jwt-abc"):
    s = MagicMock()
    s.access_token = token
    return s


def test_get_client_applies_user_jwt(monkeypatch):
    """When a user session is present, the client is authed with the user JWT."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    fake = MagicMock()
    with patch("lib.supabase_client.create_client", return_value=fake):
        with patch.dict("streamlit.session_state", {"session": _session("jwt-abc")}, clear=True):
            from lib.supabase_client import get_client
            client = get_client()
            assert client is fake
            fake.postgrest.auth.assert_called_with("jwt-abc")


def test_get_client_uses_anon_key_without_session(monkeypatch):
    """Without a session the client falls back to the anon key (no stale token)."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    fake = MagicMock()
    with patch("lib.supabase_client.create_client", return_value=fake):
        with patch.dict("streamlit.session_state", {}, clear=True):
            from lib.supabase_client import get_client
            get_client()
            fake.postgrest.auth.assert_called_with("anon-key")


def test_get_client_is_cached_per_session(monkeypatch):
    """The client is cached in session_state (built once), not rebuilt per call."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    with patch("lib.supabase_client.create_client", side_effect=lambda *a, **k: MagicMock()) as mk:
        with patch.dict("streamlit.session_state", {"session": _session()}, clear=True):
            from lib.supabase_client import get_client
            c1 = get_client()
            c2 = get_client()
            assert c1 is c2
            assert mk.call_count == 1


def test_get_client_not_cached_at_module_scope(monkeypatch):
    """No process-global client: separate sessions get isolated instances."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    with patch("lib.supabase_client.create_client", side_effect=lambda *a, **k: MagicMock()):
        from lib.supabase_client import get_client
        with patch.dict("streamlit.session_state", {"session": _session("a")}, clear=True):
            client_a = get_client()
        with patch.dict("streamlit.session_state", {"session": _session("b")}, clear=True):
            client_b = get_client()
        assert client_a is not client_b
