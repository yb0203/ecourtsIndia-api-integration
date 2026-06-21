import os
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


def _create_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_ANON_KEY"]
    return create_client(url, key)


def get_client() -> Client:
    """
    Return a Supabase client scoped to the *current Streamlit session*.

    The client is cached per-session in ``st.session_state`` — NOT at module
    scope — so the auth token of one browser session can never leak into another
    session that happens to share the same server process.

    When a user session is present, the client's data requests are authenticated
    with that user's JWT, so the database sees ``auth.uid()`` and the RLS
    policies (``auth.uid() = user_id``) pass. Without this, every DB call runs as
    the ``anon`` role with ``auth.uid()`` NULL, which makes every RLS policy fail
    — selects return empty and inserts/updates are rejected.

    The token is re-applied only when it changes (login / refresh / logout),
    which avoids rebuilding the underlying HTTP client on every Streamlit rerun.
    """
    client: Client | None = st.session_state.get("_sb_client")
    if client is None:
        client = _create_client()
        st.session_state["_sb_client"] = client
        st.session_state["_sb_token"] = None  # default header is the anon key

    session = st.session_state.get("session")
    desired = session.access_token if session is not None else None
    if st.session_state.get("_sb_token") != desired:
        _apply_token(client, desired)
        st.session_state["_sb_token"] = desired

    return client


def _apply_token(client: Client, token: str | None) -> None:
    """
    Apply ``token`` to the client's data layer (falling back to the anon key).

    This mirrors what supabase-py does internally on an auth state change
    (``_listen_to_auth_events``): update the shared Authorization header and drop
    the lazily-built sub-clients so they are rebuilt with the new header. Setting
    ``postgrest.auth()`` alone does NOT work — it writes to a header dict that
    the live HTTP session does not read.
    """
    bearer = token or os.environ["SUPABASE_ANON_KEY"]
    client.options.headers["Authorization"] = f"Bearer {bearer}"
    client._postgrest = None
    if hasattr(client, "_storage"):
        client._storage = None
    if hasattr(client, "_functions"):
        client._functions = None
