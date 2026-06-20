import streamlit as st
from datetime import datetime, timezone
from lib.auth import is_authenticated, render_login_page
from lib.db import save_case, upsert_hearing_history
from lib.ecourts_client import EcourtsClient, CaseSearchResult

if not is_authenticated():
    render_login_page()
    st.stop()

st.title("Add New Case")


# ── Dropdown data ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_court_options() -> dict[str, str]:
    """Returns {display_name: court_code}. Tries API first, falls back to common courts."""
    try:
        api = EcourtsClient()
        data = api.get_court_structure()
        courts = data.get("courts", [])
        if courts:
            return {c["name"]: c["code"] for c in courts}
    except Exception:
        pass
    return {
        "Andhra Pradesh High Court": "APHC",
        "Bombay High Court": "BOMHC",
        "Calcutta High Court": "CALHC",
        "Delhi High Court": "DELHC",
        "Jharkhand High Court": "JHKHC",
        "Karnataka High Court": "KARHC",
        "Madras High Court": "MADHC",
        "Commercial Court Hyderabad": "COMHYD",
        "Commercial Court Raipur": "COMRPR",
        "District Court Visakhapatnam": "DCVIZ",
        "District Court Gajuwaka Visakhapatnam": "DCGAJ",
        "NCLT Calcutta": "NCLTCAL",
        "NCLAT New Delhi": "NCLAT",
        "CGIT Dhanbad": "CGITDHN",
        "MSME Facilitation Council Ranchi": "MSMERN",
        "MSME Facilitation Council Bhavnagar": "MSMEBHV",
        "MP State Tribunal Bhopal": "MPSTB",
    }


@st.cache_data(ttl=3600, show_spinner=False)
def load_case_type_options() -> list[str]:
    """Returns list of case types. Tries API first, falls back to common types."""
    try:
        api = EcourtsClient()
        data = api.get_enums()
        case_types = data.get("case_types", [])
        if case_types:
            return sorted(case_types)
    except Exception:
        pass
    return [
        "AP COM",
        "Arb. MJC",
        "CAOP",
        "CEP",
        "Company Appeal (AT) (Insolvency)",
        "COP",
        "CS",
        "EP",
        "EPFA",
        "I.A.",
        "JHMSEFC",
        "OMP (COMM.)",
        "OMP (ENF.) (COMM.)",
        "W.P",
    ]


court_options = load_court_options()
case_type_options = load_case_type_options()

# ── Step 1: Search form ───────────────────────────────────────────────────
st.subheader("Step 1: Search for the case on eCourts")

with st.form("case_search"):
    col1, col2 = st.columns(2)
    with col1:
        selected_court_name = st.selectbox(
            "Court",
            options=list(court_options.keys()),
            index=None,
            placeholder="Select a court…",
        )
        case_number = st.text_input("Case Number", placeholder="e.g. 422")
    with col2:
        case_type = st.selectbox(
            "Case Type",
            options=case_type_options,
            index=None,
            placeholder="Select case type…",
        )
        year = st.number_input("Year", min_value=1990, max_value=2030, value=2025, step=1)

    submitted = st.form_submit_button("Search eCourts", type="primary", use_container_width=True)

if submitted:
    if not all([selected_court_name, case_type, case_number, year]):
        st.error("All four fields are required.")
        st.stop()

    court_code = court_options[selected_court_name]

    try:
        api = EcourtsClient()
        result: CaseSearchResult | None = api.search_case(court_code, case_type, str(case_number), int(year))
        if result is None:
            st.warning("No case found. Please check the court, case type, number, and year.")
            st.stop()
        st.session_state["search_result"] = result
    except Exception as e:
        st.error(f"API error: {e}")
        st.stop()

# ── Step 2: Preview + save ────────────────────────────────────────────────
if "search_result" in st.session_state:
    result: CaseSearchResult = st.session_state["search_result"]

    st.divider()
    st.subheader("Step 2: Review fetched details")

    with st.container(border=True):
        col1, col2 = st.columns(2)
        col1.markdown(f"**Court:** {result.court_name}")
        col1.markdown(f"**State:** {result.state}")
        col1.markdown(f"**Petitioner:** {result.petitioner}")
        col1.markdown(f"**Respondent:** {result.respondent}")
        col2.markdown(f"**Judge:** {result.judge}")
        col2.markdown(f"**Filing Date:** {result.filing_date or '—'}")
        col2.markdown(f"**Next Hearing:** {result.next_hearing_date or '—'}")
        col2.markdown(f"**Court Status:** {result.court_status}")

    st.divider()
    st.subheader("Step 3: Add your notes")

    with st.form("save_case"):
        col1, col2 = st.columns(2)
        with col1:
            client_name = st.text_input("Client Name", placeholder="e.g. MBECL")
            local_counsel = st.text_input("Local Counsel", placeholder="e.g. Adv. Sharma")
        with col2:
            amount_at_stake = st.number_input(
                "Amount at Stake (₹)", min_value=0.0, step=100000.0, format="%.0f"
            )
            lawyer_status = st.selectbox("Your Status", ["Active", "Pending-TBF", "Disposed"])

        background_notes = st.text_area("Background Notes", placeholder="Brief background of the case...")
        action_items = st.text_area("Action Items", placeholder="What needs to happen next...")

        save_submitted = st.form_submit_button("Save Case", type="primary", use_container_width=True)

    if save_submitted:
        case_data = {
            "court_code": result.court_code,
            "case_type": result.case_type,
            "case_number": result.case_number,
            "year": int(result.year),
            "court_name": result.court_name,
            "state": result.state,
            "petitioner": result.petitioner,
            "respondent": result.respondent,
            "judge": result.judge,
            "filing_date": result.filing_date,
            "next_hearing_date": result.next_hearing_date,
            "court_status": result.court_status,
            "client_name": client_name or None,
            "amount_at_stake": float(amount_at_stake) if amount_at_stake else None,
            "local_counsel": local_counsel or None,
            "background_notes": background_notes or None,
            "action_items": action_items or None,
            "lawyer_status": lawyer_status,
            "last_refreshed_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            api = EcourtsClient()
            saved = save_case(case_data)

            hearings = api.get_hearing_history(
                result.court_code, result.case_type, result.case_number, result.year
            )
            if hearings:
                upsert_hearing_history(
                    saved["id"],
                    [{"hearing_date": h.hearing_date, "purpose": h.purpose, "outcome": h.outcome}
                     for h in hearings],
                )

            del st.session_state["search_result"]
            st.success("Case saved successfully!")
            st.query_params["case_id"] = saved["id"]
            st.switch_page("pages/4_Case_Detail.py")
        except Exception as e:
            st.error(f"Failed to save case: {e}")
