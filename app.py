import streamlit as st
from lib.auth import is_authenticated, render_login_page, logout, get_user_email, handle_oauth_callback

st.set_page_config(
    page_title="Legal Dashboard",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Handle Google OAuth redirect callback before anything else
if handle_oauth_callback():
    st.rerun()

if not is_authenticated():
    render_login_page()
    st.stop()

with st.sidebar:
    st.title("⚖️ Legal Dashboard")
    st.caption(f"Signed in as {get_user_email()}")
    st.divider()
    if st.button("Sign Out", use_container_width=True):
        logout()
        st.rerun()

st.title("⚖️ Legal Dashboard")
st.write("Use the sidebar to navigate between pages.")
