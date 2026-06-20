import streamlit as st
import pandas as pd
from lib.auth import is_authenticated, render_login_page
from lib.db import get_all_cases, update_case_from_refresh, upsert_hearing_history
from lib.ecourts_client import EcourtsClient

if not is_authenticated():
    render_login_page()
    st.stop()

st.title("My Cases")


def refresh_single_case(case: dict) -> None:
    try:
        api = EcourtsClient()
        refresh_data = api.refresh_case(
            case["court_code"], case["case_type"], case["case_number"], case["year"]
        )
        update_case_from_refresh(case["id"], refresh_data)
        hearings = api.get_hearing_history(
            case["court_code"], case["case_type"], case["case_number"], case["year"]
        )
        if hearings:
            upsert_hearing_history(
                case["id"],
                [{"hearing_date": h.hearing_date, "purpose": h.purpose, "outcome": h.outcome}
                 for h in hearings],
            )
    except Exception as e:
        st.warning(f"Could not refresh {case['case_number']}: {e}")


cases = get_all_cases()

if not cases:
    st.info("No cases saved yet. Go to **Add New Case** to get started.")
    st.stop()

# ── Filters ───────────────────────────────────────────────────────────────
df = pd.DataFrame(cases)

filter_col1, filter_col2, filter_col3 = st.columns(3)
with filter_col1:
    clients = ["All"] + sorted(df["client_name"].dropna().unique().tolist())
    selected_client = st.selectbox("Client", clients)
with filter_col2:
    statuses = ["All"] + sorted(df["lawyer_status"].dropna().unique().tolist())
    selected_status = st.selectbox("Status", statuses)
with filter_col3:
    courts = ["All"] + sorted(df["court_name"].dropna().unique().tolist())
    selected_court = st.selectbox("Forum", courts)

filtered = df.copy()
if selected_client != "All":
    filtered = filtered[filtered["client_name"] == selected_client]
if selected_status != "All":
    filtered = filtered[filtered["lawyer_status"] == selected_status]
if selected_court != "All":
    filtered = filtered[filtered["court_name"] == selected_court]

# ── Refresh All ───────────────────────────────────────────────────────────
if st.button("🔄 Refresh All Cases", type="secondary"):
    progress = st.progress(0)
    for i, case in enumerate(cases):
        refresh_single_case(case)
        progress.progress((i + 1) / len(cases))
    st.success("All cases refreshed.")
    st.rerun()

st.divider()

# ── Case table ────────────────────────────────────────────────────────────
st.write(f"Showing **{len(filtered)}** cases")

for _, row in filtered.iterrows():
    case_label = f"{row['case_number']}/{row['year']} — {row.get('court_name', '')} — {row.get('petitioner', '')} vs {row.get('respondent', '')}"
    ndoh = row.get("next_hearing_date", "")
    status = row.get("lawyer_status", "")
    client = row.get("client_name", "")

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([4, 2, 2, 1])
        c1.markdown(f"**{case_label}**")
        c2.caption(f"Client: {client}")
        c3.caption(f"NDOH: {ndoh}")
        c4.caption(status)
        if st.button("View Details", key=f"view_{row['id']}"):
            st.query_params["case_id"] = row["id"]
            st.switch_page("pages/4_Case_Detail.py")
