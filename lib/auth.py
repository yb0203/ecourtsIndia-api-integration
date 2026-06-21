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


def signup_with_email(email: str, password: str) -> bool:
    """Returns True if session is immediately available (email confirmation disabled)."""
    client = get_client()
    response = client.auth.sign_up({"email": email, "password": password})
    if response.session:
        st.session_state["session"] = response.session
        return True
    return False


def get_google_oauth_url() -> str:
    client = get_client()
    app_url = os.environ.get("APP_URL", "http://localhost:8501")
    response = client.auth.sign_in_with_oauth({
        "provider": "google",
        "options": {"redirect_to": app_url},
    })
    return response.url


def handle_oauth_callback() -> bool:
    """Check for OAuth callback code in URL and exchange for session. Returns True if handled."""
    code = st.query_params.get("code")
    if code and not is_authenticated():
        try:
            client = get_client()
            response = client.auth.exchange_code_for_session({"auth_code": code})
            st.session_state["session"] = response.session
            st.query_params.clear()
            return True
        except Exception:
            pass
    return False


def logout() -> None:
    client = get_client()
    client.auth.sign_out()
    st.session_state.pop("session", None)
    # Drop the cached per-session client so the next call rebuilds a clean,
    # unauthenticated one instead of reusing a client with a stale token.
    st.session_state.pop("_sb_client", None)


def render_login_page() -> None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("⚖️ Legal Dashboard")
        st.markdown("Track your cases. Powered by eCourts India.")
        st.divider()

        # Google sign-in (shown first, primary CTA)
        try:
            oauth_url = get_google_oauth_url()
            st.link_button("Continue with Google", oauth_url, use_container_width=True, type="primary")
        except Exception:
            st.button("Continue with Google", use_container_width=True, disabled=True,
                      help="Enable Google provider in Supabase Authentication → Providers to use this")

        st.markdown("<div style='text-align:center; color:gray; padding: 8px 0'>or</div>", unsafe_allow_html=True)

        # Toggle Sign In / Create Account
        mode = st.radio("", ["Sign In", "Create Account"], horizontal=True, label_visibility="collapsed", key="auth_mode")

        email = st.text_input("Email", placeholder="you@example.com", key="auth_email")
        password = st.text_input("Password", type="password", placeholder="Min. 6 characters", key="auth_password")

        if mode == "Sign In":
            if st.button("Sign In", type="secondary", use_container_width=True):
                if not email or not password:
                    st.error("Please enter your email and password.")
                else:
                    try:
                        login_with_email(email, password)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Login failed: {e}")

        else:
            confirm_password = st.text_input("Confirm Password", type="password", key="auth_confirm")
            if st.button("Create Account", type="secondary", use_container_width=True):
                if not email or not password:
                    st.error("Please fill in all fields.")
                elif password != confirm_password:
                    st.error("Passwords do not match.")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    try:
                        session_ready = signup_with_email(email, password)
                        if session_ready:
                            st.rerun()
                        else:
                            st.success("Account created! Check your email to confirm, then sign in.")
                    except Exception as e:
                        st.error(f"Sign up failed: {e}")
