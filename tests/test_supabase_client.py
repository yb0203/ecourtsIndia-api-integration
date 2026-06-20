import os
import pytest

def test_get_client_returns_client(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-key")

    import lib.supabase_client as sc
    sc._client = None

    from lib.supabase_client import get_client
    client = get_client()
    assert client is not None

def test_get_client_is_singleton(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-key")

    import lib.supabase_client as sc
    sc._client = None

    from lib.supabase_client import get_client
    c1 = get_client()
    c2 = get_client()
    assert c1 is c2
