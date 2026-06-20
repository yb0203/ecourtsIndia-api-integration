import streamlit as st
from datetime import datetime, timezone
from lib.auth import is_authenticated, render_login_page
from lib.db import save_case, upsert_hearing_history, upsert_orders
from lib.ecourts_client import EcourtsClient, CaseDetail

if not is_authenticated():
    render_login_page()
    st.stop()

st.title("Add New Case")

# ── How to find CNR ────────────────────────────────────────────────────────
with st.expander("ℹ️ How to find the CNR number for a case", expanded=False):
    st.markdown("""
**CNR (Case Number Record)** is the unique identifier used by the eCourts system for every case.

**To find the CNR:**
1. Go to [ecourtsindia.com → Ecourts Search](https://ecourtsindia.com/dashboard/ecourts-search)
2. Search by petitioner name, respondent name, or case number
3. Click on the case — the CNR is shown at the top (e.g. `DLHC010004222025`)
4. Copy and paste it below

Alternatively, the CNR is printed on court notices and cause list entries.
""")

# ── CNR Search ─────────────────────────────────────────────────────────────
st.subheader("Step 1: Enter CNR Number")

with st.form("cnr_search"):
    cnr_input = st.text_input(
        "CNR Number",
        placeholder="e.g. DLHC010004222025",
        help="16-character unique case identifier from eCourts"
    ).strip().upper()

    col1, col2 = st.columns([3, 1])
    with col1:
        submitted = st.form_submit_button(
            "Fetch Case Details", type="primary", use_container_width=True
        )
    with col2:
        st.link_button(
            "Search on eCourtsIndia →",
            "https://ecourtsindia.com/dashboard/ecourts-search",
            use_container_width=True,
        )

if submitted:
    if not cnr_input:
        st.error("Please enter a CNR number.")
        st.stop()
    if len(cnr_input) < 10:
        st.error("CNR looks too short — it should be at least 10 characters.")
        st.stop()

    with st.spinner("Fetching from eCourts…"):
        try:
            api = EcourtsClient()
            detail: CaseDetail | None = api.get_case_by_cnr(cnr_input)
            if detail is None:
                st.warning(
                    f"No case found for CNR `{cnr_input}`. "
                    "Please double-check the number — CNRs are case-sensitive and must be exact."
                )
                st.stop()
            st.session_state["search_result"] = detail
        except Exception as e:
            st.error(f"API error: {e}")
            st.stop()

# ── Preview ────────────────────────────────────────────────────────────────
if "search_result" in st.session_state:
    detail: CaseDetail = st.session_state["search_result"]

    st.divider()
    st.subheader("Step 2: Confirm case details")

    with st.container(border=True):
        col1, col2 = st.columns(2)
        col1.markdown(f"**CNR:** `{detail.cnr}`")
        col1.markdown(f"**Court:** {detail.court_name}")
        col1.markdown(f"**State:** {detail.state}")
        col1.markdown(f"**Case Type:** {detail.case_type}")
        col1.markdown(f"**Case Number:** {detail.case_number}")
        col2.markdown(f"**Petitioner:** {detail.petitioner or '—'}")
        col2.markdown(f"**Respondent:** {detail.respondent or '—'}")
        col2.markdown(f"**Judge:** {detail.judge or '—'}")
        col2.markdown(f"**Filing Date:** {detail.filing_date or '—'}")
        col2.markdown(f"**Next Hearing (NDOH):** {detail.next_hearing_date or '—'}")
        col2.markdown(f"**Status:** {detail.court_status or '—'}")

    if detail.hearings:
        with st.expander(f"📅 Hearing History ({len(detail.hearings)} dates)"):
            for h in sorted(detail.hearings, key=lambda x: x.hearing_date, reverse=True):
                st.caption(f"{h.hearing_date} — {h.purpose}")

    if detail.orders:
        with st.expander(f"📄 Orders ({len(detail.orders)} found)"):
            for o in detail.orders:
                st.caption(f"{o.order_date}")

    if st.button("← Wrong case? Search again", type="secondary"):
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
            lawyer_status = st.selectbox(
                "Your Status", ["Active", "Pending-TBF", "Disposed"]
            )

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
