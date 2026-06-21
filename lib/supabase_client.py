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

    When a user session exists, the client's PostgREST requests are
    authenticated with that user's JWT, so the database sees ``auth.uid()`` and
    RLS policies (``auth.uid() = user_id``) pass. Without this, every DB call
    runs as the ``anon`` role with ``auth.uid()`` NULL, which makes every RLS
    policy fail — selects return empty and inserts/updates are rejected. The
    token is re-applied on every call because Streamlit re-runs the script on
    each interaction.
    """
    client: Client | None = st.session_state.get("_sb_client")
    if client is None:
        client = _create_client()
        st.session_state["_sb_client"] = client

    _apply_auth(client)
    return client


def _apply_auth(client: Client) -> None:
    """Keep the PostgREST Authorization header in sync with the session token."""
    session = st.session_state.get("session")
    if session is not None:
        client.postgrest.auth(session.access_token)
    else:
        # Reset to the anon key after sign-out so a stale token isn't reused.
        client.postgrest.auth(os.environ["SUPABASE_ANON_KEY"])
