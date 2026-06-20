import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from lib.auth import is_authenticated, render_login_page
from lib.db import get_all_cases

if not is_authenticated():
    render_login_page()
    st.stop()

st.title("Dashboard")

cases = get_all_cases()

if not cases:
    st.info("No cases saved yet. Go to **Add New Case** to get started.")
    st.stop()

df = pd.DataFrame(cases)
df["next_hearing_date"] = pd.to_datetime(df["next_hearing_date"], errors="coerce")

# ── Metric cards ──────────────────────────────────────────────────────────
today = date.today()
week_end = today + timedelta(days=7)
month_end = today + timedelta(days=30)

total_active = len(df[df["lawyer_status"] != "Disposed"])
hearings_this_week = len(
    df[
        (df["next_hearing_date"].dt.date >= today)
        & (df["next_hearing_date"].dt.date <= week_end)
    ]
)
hearings_this_month = len(
    df[
        (df["next_hearing_date"].dt.date >= today)
        & (df["next_hearing_date"].dt.date <= month_end)
    ]
)
disposed = len(df[df["lawyer_status"] == "Disposed"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Active Cases", total_active)
col2.metric("Hearings This Week", hearings_this_week)
col3.metric("Hearings This Month", hearings_this_month)
col4.metric("Disposed Cases", disposed)

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Cases by Forum")
    forum_counts = df["court_name"].fillna("Unknown").value_counts().reset_index()
    forum_counts.columns = ["Forum", "Count"]
    fig_forum = px.bar(
        forum_counts, x="Count", y="Forum", orientation="h",
        color_discrete_sequence=["#4F8EF7"]
    )
    fig_forum.update_layout(yaxis_title="", xaxis_title="Cases", height=350)
    st.plotly_chart(fig_forum, use_container_width=True)

with chart_col2:
    st.subheader("Cases by Status")
    status_counts = df["lawyer_status"].fillna("Active").value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    fig_status = px.pie(
        status_counts, names="Status", values="Count", hole=0.4,
        color_discrete_sequence=["#4F8EF7", "#F4A261", "#E76F51"]
    )
    fig_status.update_layout(height=350)
    st.plotly_chart(fig_status, use_container_width=True)

st.divider()

# ── Upcoming hearings ─────────────────────────────────────────────────────
st.subheader("Upcoming Hearings — Next 14 Days")
upcoming = df[
    (df["next_hearing_date"].dt.date >= today)
    & (df["next_hearing_date"].dt.date <= today + timedelta(days=14))
].sort_values("next_hearing_date")

if upcoming.empty:
    st.info("No hearings in the next 14 days.")
else:
    display = upcoming[[
        "case_number", "year", "court_name", "petitioner",
        "respondent", "client_name", "next_hearing_date", "lawyer_status"
    ]].copy()
    display["Case"] = display["case_number"] + "/" + display["year"].astype(str)
    display["Parties"] = display["petitioner"] + " vs " + display["respondent"]
    display["NDOH"] = display["next_hearing_date"].dt.strftime("%d %b %Y")
    st.dataframe(
        display[["Case", "court_name", "Parties", "client_name", "NDOH", "lawyer_status"]].rename(
            columns={
                "court_name": "Court",
                "client_name": "Client",
                "lawyer_status": "Status",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
