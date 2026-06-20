import streamlit as st
from datetime import datetime, timezone
from lib.auth import is_authenticated, render_login_page
from lib.db import save_case, upsert_hearing_history, upsert_orders
from lib.ecourts_client import EcourtsClient, CaseDetail

if not is_authenticated():
    render_login_page()
    st.stop()

st.title("Add New Case")


# ── Dropdown data (cached 1 hour) ──────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_court_options() -> dict[str, str]:
    """Returns {display_name: court_code} from API enums."""
    try:
        api = EcourtsClient()
        enums = api.get_enums()
        courts = enums.get("courtCode", [])
        if courts:
            return {
                c["description"]: c["code"]
                for c in courts
                if c["code"] not in ("UNKNOWN", "") and c.get("description")
            }
    except Exception:
        pass
    # Hardcoded fallback with verified court codes
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
        "Gauhati High Court, Gauhati Bench": "GAHC01",
        "High Court of Gujarat, Ahmedabad": "GJHC24",
    }


@st.cache_data(ttl=3600, show_spinner=False)
def load_case_type_options() -> list[tuple[str, str]]:
    """Returns list of (display_label, code) from API enums."""
    try:
        api = EcourtsClient()
        enums = api.get_enums()
        types = enums.get("caseType", [])
        if types:
            return sorted(
                [(f"{c['description']} ({c['code']})", c["code"])
                 for c in types
                 if c["code"] not in ("UNKNOWN", "") and c.get("description")],
                key=lambda x: x[0],
            )
    except Exception:
        pass
    return [
        ("Anticipatory Bail Application (ABA)", "ABA"),
        ("Arbitration Case / DC (Arb)", "Arb"),
        ("Arbitration Petition (Arb_Pet)", "Arb_Pet"),
        ("Civil Appeal (CA)", "CA"),
        ("Civil Miscellaneous Appeal (CMA)", "CMA"),
        ("Company Petition (COP)", "COP"),
        ("Commercial Suit (COM_S)", "COM_S"),
        ("Execution Petition (EP)", "EP"),
        ("Miscellaneous Application (MA)", "MA"),
        ("Original Miscellaneous Petition (OMP)", "OMP"),
        ("Writ Appeal (WA)", "WA"),
        ("Writ Petition (WP)", "WP"),
    ]


court_options = load_court_options()
case_type_options = load_case_type_options()

# ── Step 1: Search form ────────────────────────────────────────────────────
st.subheader("Step 1: Enter case details")

with st.form("case_search"):
    col1, col2 = st.columns(2)

    with col1:
        court_names = list(court_options.keys())
        selected_court_name = st.selectbox(
            "Court",
            options=court_names,
            index=None,
            placeholder="Select a court…",
        )
        case_number = st.text_input(
            "Case Number",
            placeholder="e.g. 422",
            help="Enter the numeric case number only (e.g. 422 for OMP 422/2025)",
        )

    with col2:
        type_labels = [label for label, _ in case_type_options]
        type_codes  = [code  for _, code  in case_type_options]
        selected_type_label = st.selectbox(
            "Case Type",
            options=type_labels,
            index=None,
            placeholder="Select case type…",
        )
        year = st.number_input("Year", min_value=1990, max_value=2030, value=2025, step=1)

    submitted = st.form_submit_button(
        "Search eCourts", type="primary", use_container_width=True
    )

if submitted:
    if not all([selected_court_name, selected_type_label, case_number, year]):
        st.error("All four fields are required.")
        st.stop()

    court_code = court_options[selected_court_name]
    case_type  = type_codes[type_labels.index(selected_type_label)]

    with st.spinner("Looking up case on eCourts…"):
        try:
            api = EcourtsClient()
            detail: CaseDetail | None = api.search_case(
                court_code, case_type, case_number.strip(), int(year)
            )
            if detail is None:
                st.warning(
                    f"No case found for **{case_number}/{year}** at **{selected_court_name}**. "
                    "Please verify the case number and year. Note that not all courts have "
                    "digitised records on eCourts."
                )
                st.stop()
            st.session_state["search_result"] = detail
        except Exception as e:
            st.error(f"API error: {e}")
            st.stop()

# ── Step 2: Preview ────────────────────────────────────────────────────────
if "search_result" in st.session_state:
    detail: CaseDetail = st.session_state["search_result"]

    st.divider()
    st.subheader("Step 2: Confirm case details")

    with st.container(border=True):
        col1, col2 = st.columns(2)
        col1.markdown(f"**Court:** {detail.court_name}")
        col1.markdown(f"**State:** {detail.state}")
        col1.markdown(f"**Case Type:** {detail.case_type}")
        col1.markdown(f"**Case Number:** {detail.case_number}")
        col1.markdown(f"**Filing Date:** {detail.filing_date or '—'}")
        col2.markdown(f"**Petitioner:** {detail.petitioner or '—'}")
        col2.markdown(f"**Respondent:** {detail.respondent or '—'}")
        col2.markdown(f"**Judge:** {detail.judge or '—'}")
        col2.markdown(f"**Next Hearing (NDOH):** {detail.next_hearing_date or '—'}")
        col2.markdown(f"**Status:** {detail.court_status or '—'}")

    if detail.hearings:
        with st.expander(f"📅 Hearing History ({len(detail.hearings)} dates)"):
            for h in detail.hearings:
                st.caption(f"{h.hearing_date} — {h.purpose}")

    if detail.orders:
        with st.expander(f"📄 Orders ({len(detail.orders)} found)"):
            for o in detail.orders:
                st.caption(f"{o.order_date}")

    st.warning(
        "⚠️ If the details above don't match your case, the case number or year "
        "may be slightly different in the eCourts system. Try adjusting and searching again."
    )

    if st.button("← Search Again", type="secondary"):
        del st.session_state["search_result"]
        st.rerun()

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

        background_notes = st.text_area(
            "Background Notes", placeholder="Brief background of the case…"
        )
        action_items = st.text_area(
            "Action Items", placeholder="What needs to happen next…"
        )

        save_submitted = st.form_submit_button(
            "Save Case", type="primary", use_container_width=True
        )

    if save_submitted:
        case_data = {
            "cnr": detail.cnr,
            "court_code": detail.court_code,
            "case_type": detail.case_type,
            "case_number": detail.case_number,
            "year": int(detail.year),
            "court_name": detail.court_name,
            "state": detail.state,
            "petitioner": detail.petitioner,
            "respondent": detail.respondent,
            "judge": detail.judge,
            "filing_date": detail.filing_date,
            "next_hearing_date": detail.next_hearing_date,
            "court_status": detail.court_status,
            "client_name": client_name or None,
            "amount_at_stake": float(amount_at_stake) if amount_at_stake else None,
            "local_counsel": local_counsel or None,
            "background_notes": background_notes or None,
            "action_items": action_items or None,
            "lawyer_status": lawyer_status,
            "last_refreshed_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            saved = save_case(case_data)

            if detail.hearings:
                upsert_hearing_history(
                    saved["id"],
                    [{"hearing_date": h.hearing_date,
                      "purpose": h.purpose,
                      "outcome": h.outcome}
                     for h in detail.hearings],
                )
            if detail.orders:
                upsert_orders(
                    saved["id"],
                    [{"order_date": o.order_date,
                      "order_number": o.order_number,
                      "pdf_url": o.pdf_url}
                     for o in detail.orders],
                )

            del st.session_state["search_result"]
            st.success("Case saved successfully!")
            st.query_params["case_id"] = saved["id"]
            st.switch_page("pages/4_Case_Detail.py")
        except Exception as e:
            st.error(f"Failed to save case: {e}")
