import os
import streamlit as st
from dotenv import load_dotenv
from lib.supabase_client import get_client

load_dotenv()


def is_authenticated() -> bool:
    return st.session_state.get("session") is not None


def get_user_id() -> str | None:
    session = st.session_state.get("session")
    if session:
        return session.user.id
    return None


def get_user_email() -> str | None:
    session = st.session_state.get("session")
    if session:
        return session.user.email
    return None


def login_with_email(email: str, password: str) -> None:
    client = get_client()
    response = client.auth.sign_in_with_password({"email": email, "password": password})
    st.session_state["session"] = response.session


def get_google_oauth_url() -> str:
    client = get_client()
    app_url = os.environ.get("APP_URL", "http://localhost:8501")
    response = client.auth.sign_in_with_oauth({
        "provider": "google",
        "options": {"redirect_to": app_url},
    })
    return response.url


def logout() -> None:
    client = get_client()
    client.auth.sign_out()
    st.session_state.pop("session", None)


def render_login_page() -> None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("⚖️ Legal Dashboard")
        st.markdown("Track your cases. Powered by eCourts India.")
        st.divider()

        tab_email, tab_google = st.tabs(["Email & Password", "Google"])

        with tab_email:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Sign In", type="primary", use_container_width=True):
                try:
                    login_with_email(email, password)
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")

        with tab_google:
            st.markdown("Click below to sign in with your Google account.")
            try:
                oauth_url = get_google_oauth_url()
                st.link_button("Sign in with Google", oauth_url, use_container_width=True)
            except Exception:
                st.warning("Google sign-in requires SUPABASE_URL and SUPABASE_ANON_KEY to be set.")
