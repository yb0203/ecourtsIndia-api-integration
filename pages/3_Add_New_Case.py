import streamlit as st
from datetime import datetime, timezone, date
from lib.auth import is_authenticated, render_login_page
from lib.db import save_case, upsert_hearing_history
from lib.ecourts_client import EcourtsClient, CaseDetail

if not is_authenticated():
    render_login_page()
    st.stop()

st.title("Add New Case")

# ── Court options (cached from API enums) ──────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_court_options() -> dict[str, str]:
    try:
        api = EcourtsClient()
        enums = api.get_enums()
        courts = enums.get("courtCode", [])
        if courts:
            return {c["description"]: c["code"] for c in courts if c["code"] not in ("UNKNOWN", "") and c.get("description")}
    except Exception:
        pass
    return {
        "High Court of Andhra Pradesh, Amaravati": "APHC01",
        "Patna High Court, Bihar": "BRHC01",
        "High Court of Chhattisgarh, Bilaspur": "CGHC01",
        "High Court of Delhi, Delhi": "DLHC01",
        "High Court for the State of Telangana, Hyderabad": "HBHC01",
        "Bombay High Court, Mumbai": "HCBM01",
        "Madras High Court, Chennai": "HCMA01",
        "Jharkhand High Court, Ranchi": "JHHC01",
        "High Court of Karnataka, Bengaluru": "KAHC01",
        "Calcutta High Court, West Bengal": "WBHC01",
        "Commercial Court Hyderabad": "COMHYD",
        "District Court Visakhapatnam": "DCVIZ",
        "NCLT Calcutta": "NCLTCAL",
        "NCLAT New Delhi": "NCLAT",
        "CGIT Dhanbad": "CGITDHN",
        "MSME Facilitation Council Ranchi": "MSMERN",
        "MP State Tribunal Bhopal": "MPSTB",
        "Commercial Court Raipur": "COMRPR",
    }

court_options = load_court_options()
court_names = list(court_options.keys())

# ── Case details form ──────────────────────────────────────────────────────
st.subheader("Case Details")

with st.form("add_case_form"):

    # Row 1 — Court + Forum details
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        selected_court = st.selectbox("Court / Forum", options=court_names, index=None, placeholder="Select court…")
    with col2:
        case_type = st.text_input("Case Type", placeholder="e.g. OMP (COMM.), W.P, COP")
    with col3:
        year = st.number_input("Year", min_value=1990, max_value=2030, value=2025, step=1)

    col1, col2 = st.columns(2)
    with col1:
        case_number = st.text_input("Case Number", placeholder="e.g. 422")
    with col2:
        client_name = st.text_input("Client Name", placeholder="e.g. MBECL")

    st.divider()

    # Row 2 — Parties
    col1, col2 = st.columns(2)
    with col1:
        petitioner = st.text_input("Petitioner", placeholder="e.g. The Singareni Collieries Company Limited")
    with col2:
        respondent = st.text_input("Respondent", placeholder="e.g. McNally Bharat Engineering Company Limited")

    col1, col2 = st.columns(2)
    with col1:
        judge = st.text_input("Judge", placeholder="e.g. Hon. Justice ABC")
    with col2:
        local_counsel = st.text_input("Local Counsel", placeholder="e.g. Adv. Sharma")

    st.divider()

    # Row 3 — Dates and status
    col1, col2, col3 = st.columns(3)
    with col1:
        filing_date = st.date_input("Filing Date", value=None)
    with col2:
        next_hearing_date = st.date_input("Next Hearing Date (NDOH)", value=None)
    with col3:
        lawyer_status = st.selectbox("Status", ["Active", "Pending-TBF", "Disposed"])

    col1, col2 = st.columns(2)
    with col1:
        court_status = st.text_input("Court Status", placeholder="e.g. Pending, Disposed")
    with col2:
        amount_at_stake = st.number_input("Amount at Stake (₹)", min_value=0.0, step=100000.0, format="%.0f")

    st.divider()

    # Row 4 — Notes
    background_notes = st.text_area(
        "Background",
        placeholder="Brief background of the case…",
        height=100,
    )
    action_items = st.text_area(
        "Remarks / Action Items",
        placeholder="Current status and what needs to happen next…",
        height=100,
    )

    save_submitted = st.form_submit_button("Save Case", type="primary", use_container_width=True)

if save_submitted:
    if not selected_court:
        st.error("Please select a court.")
        st.stop()
    if not case_number:
        st.error("Please enter a case number.")
        st.stop()

    court_code = court_options.get(selected_court, "")

    case_data = {
        "court_code": court_code,
        "case_type": case_type or None,
        "case_number": case_number,
        "year": int(year),
        "court_name": selected_court,
        "state": None,
        "petitioner": petitioner or None,
        "respondent": respondent or None,
        "judge": judge or None,
        "filing_date": filing_date.isoformat() if filing_date else None,
        "next_hearing_date": next_hearing_date.isoformat() if next_hearing_date else None,
        "court_status": court_status or None,
        "client_name": client_name or None,
        "amount_at_stake": float(amount_at_stake) if amount_at_stake else None,
        "local_counsel": local_counsel or None,
        "background_notes": background_notes or None,
        "action_items": action_items or None,
        "lawyer_status": lawyer_status,
        "last_refreshed_at": datetime.now(timezone.utc).isoformat(),
        "cnr": None,
    }

    try:
        saved = save_case(case_data)
        st.success(f"Case {case_number}/{year} saved successfully!")
        st.query_params["case_id"] = saved["id"]
        st.switch_page("pages/4_Case_Detail.py")
    except Exception as e:
        st.error(f"Failed to save case: {e}")
