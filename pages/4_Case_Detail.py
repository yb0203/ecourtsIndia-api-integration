import streamlit as st
import pandas as pd
from lib.auth import is_authenticated, render_login_page
from lib.db import (
    get_case_by_id, update_case, get_orders_for_case,
    upsert_orders, update_order_summary, get_hearing_history_for_case,
    upsert_hearing_history, update_case_from_refresh,
)
from lib.ecourts_client import EcourtsClient

if not is_authenticated():
    render_login_page()
    st.stop()

case_id = st.query_params.get("case_id")
if not case_id:
    st.error("No case selected. Go to My Cases and click a case.")
    st.stop()

case = get_case_by_id(case_id)
if not case:
    st.error("Case not found or you don't have access to it.")
    st.stop()

# ── Header ────────────────────────────────────────────────────────────────
st.title(f"{case['case_number']}/{case['year']}")
st.caption(f"{case.get('court_name', '')} · {case.get('state', '')}")

header_col1, header_col2, header_col3 = st.columns([2, 2, 1])

with header_col1:
    st.markdown(f"**Petitioner:** {case.get('petitioner', '—')}")
    st.markdown(f"**Respondent:** {case.get('respondent', '—')}")
    st.markdown(f"**Judge:** {case.get('judge', '—')}")

with header_col2:
    st.markdown(f"**Filing Date:** {case.get('filing_date', '—')}")
    st.markdown(f"**Next Hearing (NDOH):** {case.get('next_hearing_date', '—')}")
    st.markdown(f"**Court Status:** {case.get('court_status', '—')}")

with header_col3:
    st.markdown(f"**Client:** {case.get('client_name', '—')}")
    amount = case.get("amount_at_stake")
    st.markdown(f"**Amount:** {'₹{:,.0f}'.format(amount) if amount else '—'}")
    st.markdown(f"**Local Counsel:** {case.get('local_counsel', '—')}")

cnr = case.get("cnr")

if st.button("🔄 Refresh Case"):
    if not cnr:
        st.warning("This case has no CNR number — cannot refresh from eCourts.")
    else:
        with st.spinner("Fetching latest data from eCourts…"):
            try:
                api = EcourtsClient()
                detail = api.get_case_by_cnr(cnr)
                if detail:
                    update_case_from_refresh(case["id"], {
                        "next_hearing_date": detail.next_hearing_date,
                        "status": detail.court_status,
                    })
                    if detail.hearings:
                        upsert_hearing_history(
                            case["id"],
                            [{"hearing_date": h.hearing_date, "purpose": h.purpose, "outcome": h.outcome}
                             for h in detail.hearings],
                        )
                    if detail.orders:
                        upsert_orders(
                            case["id"],
                            [{"order_date": o.order_date, "order_number": o.order_number, "pdf_url": o.pdf_url}
                             for o in detail.orders],
                        )
                st.success("Case refreshed with latest data from eCourts.")
                st.rerun()
            except Exception as e:
                st.error(f"Refresh failed: {e}")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────
tab_hearings, tab_orders, tab_notes = st.tabs(["📅 Hearings", "📄 Orders", "📝 Notes"])

# ── Hearings tab ──────────────────────────────────────────────────────────
with tab_hearings:
    hearings = get_hearing_history_for_case(case_id)
    if not hearings:
        st.info("No hearing history yet. Refresh the case to load hearing dates from eCourts.")
    else:
        df_h = pd.DataFrame(hearings)[["hearing_date", "purpose", "outcome"]]
        df_h.columns = ["Date", "Purpose", "Outcome"]
        df_h["Date"] = pd.to_datetime(df_h["Date"], errors="coerce").dt.strftime("%d %b %Y")
        st.dataframe(df_h, use_container_width=True, hide_index=True)

# ── Orders tab ────────────────────────────────────────────────────────────
with tab_orders:
    if not cnr:
        st.caption("No CNR — orders cannot be fetched for this case.")

    orders = get_orders_for_case(case_id)
    if not orders:
        st.info("No orders fetched yet. Click the button above to load them.")
    else:
        for order in orders:
            with st.container(border=True):
                o_col1, o_col2, o_col3 = st.columns([2, 5, 1])
                o_col1.markdown(f"**{order.get('order_date', '—')}**")
                o_col1.caption(f"Order #{order.get('order_number', '—')}")

                summary = order.get("ai_summary")
                if summary:
                    o_col2.markdown(summary)
                else:
                    o_col2.caption("No summary yet.")
                    if o_col2.button(f"Get AI Summary (₹2.50)", key=f"summary_{order['id']}"):
                        try:
                            api = EcourtsClient()
                            s = api.get_order_summary(cnr, order["order_number"])
                            update_order_summary(order["id"], s)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")

                if order.get("pdf_url"):
                    o_col3.link_button("PDF ↓", order["pdf_url"])

# ── Notes tab ─────────────────────────────────────────────────────────────
with tab_notes:
    with st.form("edit_notes"):
        background_notes = st.text_area(
            "Background Notes",
            value=case.get("background_notes") or "",
            height=150,
        )
        action_items = st.text_area(
            "Action Items",
            value=case.get("action_items") or "",
            height=150,
        )
        lawyer_status = st.selectbox(
            "Your Status",
            ["Active", "Pending-TBF", "Disposed"],
            index=["Active", "Pending-TBF", "Disposed"].index(
                case.get("lawyer_status", "Active")
            ),
        )
        if st.form_submit_button("Save Notes", type="primary"):
            try:
                update_case(case_id, {
                    "background_notes": background_notes,
                    "action_items": action_items,
                    "lawyer_status": lawyer_status,
                })
                st.success("Notes saved.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")
