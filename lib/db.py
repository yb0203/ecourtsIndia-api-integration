from datetime import datetime, timezone
from lib.supabase_client import get_client
from lib.auth import get_user_id


# ── Cases ──────────────────────────────────────────────────────────────────

def get_all_cases() -> list[dict]:
    client = get_client()
    response = (
        client.table("cases")
        .select("*")
        .eq("user_id", get_user_id())
        .order("next_hearing_date")
        .execute()
    )
    return response.data


def get_case_by_id(case_id: str) -> dict | None:
    client = get_client()
    response = (
        client.table("cases")
        .select("*")
        .eq("id", case_id)
        .eq("user_id", get_user_id())
        .single()
        .execute()
    )
    return response.data


def save_case(case_data: dict) -> dict:
    client = get_client()
    payload = {**case_data, "user_id": get_user_id()}
    response = client.table("cases").insert(payload).execute()
    return response.data[0]


def update_case(case_id: str, updates: dict) -> dict:
    client = get_client()
    response = (
        client.table("cases")
        .update(updates)
        .eq("id", case_id)
        .eq("user_id", get_user_id())
        .execute()
    )
    return response.data[0]


def update_case_from_refresh(case_id: str, refresh_data: dict) -> None:
    updates = {
        "next_hearing_date": refresh_data.get("next_hearing_date"),
        "court_status": refresh_data.get("status"),
        "last_refreshed_at": datetime.now(timezone.utc).isoformat(),
    }
    update_case(case_id, {k: v for k, v in updates.items() if v is not None})


# ── Orders ─────────────────────────────────────────────────────────────────

def get_orders_for_case(case_id: str) -> list[dict]:
    client = get_client()
    response = (
        client.table("orders")
        .select("*")
        .eq("case_id", case_id)
        .order("order_date", desc=True)
        .execute()
    )
    return response.data


def upsert_orders(case_id: str, orders: list[dict]) -> None:
    client = get_client()
    user_id = get_user_id()
    records = [
        {"case_id": case_id, "user_id": user_id, **o}
        for o in orders
    ]
    client.table("orders").upsert(records, on_conflict="case_id,order_number").execute()


def update_order_summary(order_id: str, summary: str) -> None:
    client = get_client()
    client.table("orders").update({"ai_summary": summary}).eq("id", order_id).execute()


# ── Hearing History ────────────────────────────────────────────────────────

def get_hearing_history_for_case(case_id: str) -> list[dict]:
    client = get_client()
    response = (
        client.table("hearing_history")
        .select("*")
        .eq("case_id", case_id)
        .order("hearing_date", desc=True)
        .execute()
    )
    return response.data


def upsert_hearing_history(case_id: str, hearings: list[dict]) -> None:
    client = get_client()
    user_id = get_user_id()
    records = [
        {"case_id": case_id, "user_id": user_id, **h}
        for h in hearings
    ]
    client.table("hearing_history").upsert(
        records, on_conflict="case_id,hearing_date"
    ).execute()
