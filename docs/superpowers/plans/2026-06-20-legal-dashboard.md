# Legal Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Streamlit legal case tracking dashboard backed by Supabase and the ecourtsindia.com API, with per-lawyer auth and live case data.

**Architecture:** Streamlit multi-page app with a `pages/` directory. All data lives in Supabase (3 tables: cases, orders, hearing_history). A thin Python API client wraps ecourtsindia.com. Auth is handled entirely by Supabase Auth (email/password + Google OAuth). Every DB query is scoped to the logged-in user via Supabase RLS.

**Tech Stack:** Python 3.11+, Streamlit 1.36+, supabase-py 2.x, Plotly, Pandas, Requests, pytest

---

## File Structure

```
ecourtsIndia-api-integration/
├── app.py                          # Entry point: auth guard + sidebar
├── pages/
│   ├── 1_Dashboard.py              # Home: metrics, charts, upcoming hearings
│   ├── 2_My_Cases.py               # Filterable case list + Refresh All
│   ├── 3_Add_New_Case.py           # API search form + save to Supabase
│   └── 4_Case_Detail.py            # Tabbed view: hearings, orders, notes
├── lib/
│   ├── supabase_client.py          # Supabase singleton client
│   ├── auth.py                     # Login/logout helpers + login page UI
│   ├── ecourts_client.py           # ecourtsindia.com API wrapper
│   └── db.py                       # All Supabase CRUD queries
├── supabase/
│   └── migrations/
│       └── 001_initial_schema.sql  # Tables + RLS policies
├── tests/
│   ├── test_ecourts_client.py
│   └── test_db.py
├── .env.example
├── .gitignore
└── requirements.txt
```

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: Create requirements.txt**

```
streamlit>=1.36.0
supabase>=2.4.0
python-dotenv>=1.0.0
requests>=2.31.0
pandas>=2.0.0
plotly>=5.18.0
pytest>=7.4.0
pytest-mock>=3.12.0
```

- [ ] **Step 2: Create .env.example**

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
ECOURTS_API_KEY=your-ecourts-api-key-here
APP_URL=http://localhost:8501
```

- [ ] **Step 3: Create .gitignore**

```
.env
__pycache__/
*.pyc
.pytest_cache/
.streamlit/secrets.toml
```

- [ ] **Step 4: Create empty package directories**

```bash
mkdir -p lib pages supabase/migrations tests
touch lib/__init__.py tests/__init__.py
```

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install without errors.

- [ ] **Step 6: Copy .env.example to .env and fill in values**

```bash
cp .env.example .env
# Edit .env with your actual Supabase URL and anon key
# Leave ECOURTS_API_KEY blank for now — added when API key is obtained
```

- [ ] **Step 7: Commit**

```bash
git init
git add requirements.txt .env.example .gitignore
git commit -m "chore: project setup and dependencies"
```

---

## Task 2: Supabase Schema

**Files:**
- Create: `supabase/migrations/001_initial_schema.sql`

**Note:** Run this SQL in your Supabase project's SQL Editor (Dashboard → SQL Editor → New Query). You do NOT run this locally with a migration tool — paste and execute directly.

- [ ] **Step 1: Write the migration file**

Create `supabase/migrations/001_initial_schema.sql`:

```sql
-- Enable UUID generation
create extension if not exists "uuid-ossp";

-- ============================================================
-- CASES TABLE
-- ============================================================
create table cases (
  id                 uuid primary key default uuid_generate_v4(),
  user_id            uuid not null references auth.users(id) on delete cascade,

  -- API lookup keys (required to call ecourtsindia.com)
  court_code         text not null,
  case_type          text not null,
  case_number        text not null,
  year               integer not null,

  -- API-fetched fields (populated on save and refresh)
  court_name         text,
  state              text,
  petitioner         text,
  respondent         text,
  judge              text,
  filing_date        date,
  next_hearing_date  date,
  court_status       text,

  -- Manually entered by lawyer
  client_name        text,
  amount_at_stake    numeric,
  local_counsel      text,
  background_notes   text,
  action_items       text,
  lawyer_status      text default 'Active'
                     check (lawyer_status in ('Active', 'Pending-TBF', 'Disposed')),

  last_refreshed_at  timestamptz,
  created_at         timestamptz default now()
);

-- ============================================================
-- ORDERS TABLE
-- ============================================================
create table orders (
  id            uuid primary key default uuid_generate_v4(),
  case_id       uuid not null references cases(id) on delete cascade,
  user_id       uuid not null references auth.users(id) on delete cascade,
  order_date    date,
  order_number  text,
  pdf_url       text,
  ai_summary    text,
  created_at    timestamptz default now(),
  unique (case_id, order_number)
);

-- ============================================================
-- HEARING HISTORY TABLE
-- ============================================================
create table hearing_history (
  id            uuid primary key default uuid_generate_v4(),
  case_id       uuid not null references cases(id) on delete cascade,
  user_id       uuid not null references auth.users(id) on delete cascade,
  hearing_date  date,
  purpose       text,
  outcome       text,
  created_at    timestamptz default now(),
  unique (case_id, hearing_date)
);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
alter table cases          enable row level security;
alter table orders         enable row level security;
alter table hearing_history enable row level security;

-- Cases policies
create policy "cases: select own"  on cases for select  using (auth.uid() = user_id);
create policy "cases: insert own"  on cases for insert  with check (auth.uid() = user_id);
create policy "cases: update own"  on cases for update  using (auth.uid() = user_id);
create policy "cases: delete own"  on cases for delete  using (auth.uid() = user_id);

-- Orders policies
create policy "orders: select own"  on orders for select  using (auth.uid() = user_id);
create policy "orders: insert own"  on orders for insert  with check (auth.uid() = user_id);
create policy "orders: update own"  on orders for update  using (auth.uid() = user_id);
create policy "orders: delete own"  on orders for delete  using (auth.uid() = user_id);

-- Hearing history policies
create policy "hearing_history: select own"  on hearing_history for select  using (auth.uid() = user_id);
create policy "hearing_history: insert own"  on hearing_history for insert  with check (auth.uid() = user_id);
create policy "hearing_history: update own"  on hearing_history for update  using (auth.uid() = user_id);
create policy "hearing_history: delete own"  on hearing_history for delete  using (auth.uid() = user_id);
```

- [ ] **Step 2: Run the migration in Supabase**

1. Go to your Supabase project dashboard
2. Click "SQL Editor" in the left sidebar
3. Click "New query"
4. Paste the entire contents of `supabase/migrations/001_initial_schema.sql`
5. Click "Run"

Expected output: `Success. No rows returned.`

- [ ] **Step 3: Verify tables exist**

In Supabase dashboard → Table Editor, confirm you see three tables: `cases`, `orders`, `hearing_history`.

- [ ] **Step 4: Enable Google OAuth in Supabase (for Task 4)**

1. Supabase dashboard → Authentication → Providers
2. Enable Google provider
3. Add your Google OAuth Client ID and Secret (from Google Cloud Console)
4. Add `http://localhost:8501` to the redirect URLs list

- [ ] **Step 5: Commit**

```bash
git add supabase/
git commit -m "feat: supabase schema with cases, orders, hearing_history and RLS"
```

---

## Task 3: Supabase Client

**Files:**
- Create: `lib/supabase_client.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_supabase_client.py`:

```python
import os
import pytest

def test_get_client_returns_client(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-key")

    # Reset singleton between tests
    import lib.supabase_client as sc
    sc._client = None

    from lib.supabase_client import get_client
    client = get_client()
    assert client is not None

def test_get_client_is_singleton(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-key")

    import lib.supabase_client as sc
    sc._client = None

    from lib.supabase_client import get_client
    c1 = get_client()
    c2 = get_client()
    assert c1 is c2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_supabase_client.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `lib.supabase_client` does not exist yet.

- [ ] **Step 3: Implement the client**

Create `lib/supabase_client.py`:

```python
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_ANON_KEY"]
        _client = create_client(url, key)
    return _client
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_supabase_client.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add lib/supabase_client.py tests/test_supabase_client.py
git commit -m "feat: supabase singleton client"
```

---

## Task 4: Authentication Module + Login Page

**Files:**
- Create: `lib/auth.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_auth.py`:

```python
import pytest
import streamlit as st
from unittest.mock import MagicMock, patch


def test_is_authenticated_returns_false_with_no_session():
    # Patch st.session_state to be empty
    with patch.dict("streamlit.session_state", {}, clear=True):
        from lib.auth import is_authenticated
        assert is_authenticated() is False


def test_is_authenticated_returns_true_with_session():
    mock_session = MagicMock()
    with patch.dict("streamlit.session_state", {"session": mock_session}):
        from lib.auth import is_authenticated
        assert is_authenticated() is True


def test_get_user_id_returns_none_without_session():
    with patch.dict("streamlit.session_state", {}, clear=True):
        from lib.auth import get_user_id
        assert get_user_id() is None


def test_get_user_id_returns_id_with_session():
    mock_session = MagicMock()
    mock_session.user.id = "user-123"
    with patch.dict("streamlit.session_state", {"session": mock_session}):
        from lib.auth import get_user_id
        assert get_user_id() == "user-123"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_auth.py -v
```

Expected: `ImportError` — `lib.auth` does not exist yet.

- [ ] **Step 3: Implement auth module**

Create `lib/auth.py`:

```python
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


def get_google_oauth_url() -> str:
    client = get_client()
    app_url = os.environ.get("APP_URL", "http://localhost:8501")
    response = client.auth.sign_in_with_oauth({
        "provider": "google",
        "options": {"redirect_to": app_url},
    })
    return response.url


def logout() -> None:
    client = get_client()
    client.auth.sign_out()
    st.session_state.pop("session", None)


def render_login_page() -> None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("⚖️ Legal Dashboard")
        st.markdown("Track your cases. Powered by eCourts India.")
        st.divider()

        tab_email, tab_google = st.tabs(["Email & Password", "Google"])

        with tab_email:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Sign In", type="primary", use_container_width=True):
                try:
                    login_with_email(email, password)
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")

        with tab_google:
            st.markdown("Click below to sign in with your Google account.")
            try:
                oauth_url = get_google_oauth_url()
                st.link_button("Sign in with Google", oauth_url, use_container_width=True)
            except Exception:
                st.warning("Google sign-in requires SUPABASE_URL and SUPABASE_ANON_KEY to be set.")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_auth.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add lib/auth.py tests/test_auth.py
git commit -m "feat: auth module with email and google oauth support"
```

---

## Task 5: eCourts API Client

**Files:**
- Create: `lib/ecourts_client.py`
- Create: `tests/test_ecourts_client.py`

**Note:** The exact field names in API responses will need to be verified against the actual ecourtsindia.com docs once you have the API key. The client is designed to make that adjustment easy — only the dataclass field mappings in each method need updating.

- [ ] **Step 1: Write failing tests**

Create `tests/test_ecourts_client.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
import os


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("ECOURTS_API_KEY", "test-key")


def make_mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    return mock


def test_search_case_returns_result():
    mock_resp = make_mock_response({
        "results": [{
            "court_name": "Delhi High Court",
            "state": "Delhi",
            "petitioner": "NTPC",
            "respondent": "MBECL",
            "judge": "Hon. Justice ABC",
            "filing_date": "2025-01-15",
            "next_hearing_date": "2026-07-10",
            "status": "Pending",
        }]
    })
    with patch("lib.ecourts_client.requests.get", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        result = client.search_case("DEL001", "OMP(COMM)", "422", 2025)

    assert result is not None
    assert result.court_name == "Delhi High Court"
    assert result.petitioner == "NTPC"
    assert result.next_hearing_date == "2026-07-10"


def test_search_case_returns_none_when_no_results():
    mock_resp = make_mock_response({"results": []})
    with patch("lib.ecourts_client.requests.get", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        result = client.search_case("DEL001", "OMP(COMM)", "999", 2025)

    assert result is None


def test_get_orders_returns_list():
    mock_resp = make_mock_response({
        "orders": [
            {"date": "2026-04-15", "number": "042", "pdf_url": "https://example.com/order.pdf"},
            {"date": "2026-02-10", "number": "031", "pdf_url": "https://example.com/order2.pdf"},
        ]
    })
    with patch("lib.ecourts_client.requests.get", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        orders = client.get_orders("DEL001", "OMP(COMM)", "422", 2025)

    assert len(orders) == 2
    assert orders[0].order_number == "042"
    assert orders[0].pdf_url == "https://example.com/order.pdf"


def test_get_orders_returns_empty_list_when_none():
    mock_resp = make_mock_response({"orders": []})
    with patch("lib.ecourts_client.requests.get", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        orders = client.get_orders("DEL001", "OMP(COMM)", "422", 2025)

    assert orders == []


def test_refresh_case_returns_updated_data():
    mock_resp = make_mock_response({
        "next_hearing_date": "2026-08-01",
        "status": "Pending",
    })
    with patch("lib.ecourts_client.requests.post", return_value=mock_resp):
        from lib.ecourts_client import EcourtsClient
        client = EcourtsClient()
        result = client.refresh_case("DEL001", "OMP(COMM)", "422", 2025)

    assert result["next_hearing_date"] == "2026-08-01"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_ecourts_client.py -v
```

Expected: `ImportError` — `lib.ecourts_client` does not exist yet.

- [ ] **Step 3: Implement the API client**

Create `lib/ecourts_client.py`:

```python
import os
from dataclasses import dataclass
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.ecourtsindia.com/api/partner"


@dataclass
class CaseSearchResult:
    court_code: str
    case_type: str
    case_number: str
    year: int
    court_name: str
    state: str
    petitioner: str
    respondent: str
    judge: str
    filing_date: Optional[str]
    next_hearing_date: Optional[str]
    court_status: str


@dataclass
class Order:
    order_date: str
    order_number: str
    pdf_url: str
    ai_summary: Optional[str] = None


@dataclass
class HearingRecord:
    hearing_date: str
    purpose: str
    outcome: str


class EcourtsClient:
    def __init__(self) -> None:
        self.api_key = os.environ["ECOURTS_API_KEY"]
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def search_case(
        self, court_code: str, case_type: str, case_number: str, year: int
    ) -> Optional[CaseSearchResult]:
        resp = requests.get(
            f"{BASE_URL}/search",
            params={
                "court_code": court_code,
                "case_type": case_type,
                "case_number": case_number,
                "year": year,
            },
            headers=self.headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("results"):
            return None
        r = data["results"][0]
        return CaseSearchResult(
            court_code=court_code,
            case_type=case_type,
            case_number=case_number,
            year=year,
            court_name=r.get("court_name", ""),
            state=r.get("state", ""),
            petitioner=r.get("petitioner", ""),
            respondent=r.get("respondent", ""),
            judge=r.get("judge", ""),
            filing_date=r.get("filing_date"),
            next_hearing_date=r.get("next_hearing_date"),
            court_status=r.get("status", ""),
        )

    def get_case_detail(
        self, court_code: str, case_type: str, case_number: str, year: int
    ) -> dict:
        resp = requests.get(
            f"{BASE_URL}/case",
            params={
                "court_code": court_code,
                "case_type": case_type,
                "case_number": case_number,
                "year": year,
            },
            headers=self.headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def refresh_case(
        self, court_code: str, case_type: str, case_number: str, year: int
    ) -> dict:
        resp = requests.post(
            f"{BASE_URL}/refresh",
            json={
                "court_code": court_code,
                "case_type": case_type,
                "case_number": case_number,
                "year": year,
            },
            headers=self.headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def get_orders(
        self, court_code: str, case_type: str, case_number: str, year: int
    ) -> list[Order]:
        resp = requests.get(
            f"{BASE_URL}/orders",
            params={
                "court_code": court_code,
                "case_type": case_type,
                "case_number": case_number,
                "year": year,
            },
            headers=self.headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            Order(
                order_date=o.get("date", ""),
                order_number=o.get("number", ""),
                pdf_url=o.get("pdf_url", ""),
            )
            for o in data.get("orders", [])
        ]

    def get_order_summary(self, order_number: str, court_code: str) -> str:
        resp = requests.get(
            f"{BASE_URL}/order-summary",
            params={"order_number": order_number, "court_code": court_code},
            headers=self.headers,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("summary", "")

    def get_hearing_history(
        self, court_code: str, case_type: str, case_number: str, year: int
    ) -> list[HearingRecord]:
        detail = self.get_case_detail(court_code, case_type, case_number, year)
        return [
            HearingRecord(
                hearing_date=h.get("date", ""),
                purpose=h.get("purpose", ""),
                outcome=h.get("outcome", ""),
            )
            for h in detail.get("hearing_history", [])
        ]

    def get_court_structure(self) -> dict:
        resp = requests.get(
            f"{BASE_URL}/court-structure", headers=self.headers, timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    def get_enums(self) -> dict:
        resp = requests.get(
            f"{BASE_URL}/enums", headers=self.headers, timeout=30
        )
        resp.raise_for_status()
        return resp.json()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_ecourts_client.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add lib/ecourts_client.py tests/test_ecourts_client.py
git commit -m "feat: ecourts api client with search, refresh, and orders"
```

---

## Task 6: Database Query Layer

**Files:**
- Create: `lib/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_db.py`:

```python
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_client():
    mock = MagicMock()
    with patch("lib.db.get_client", return_value=mock):
        with patch("lib.db.get_user_id", return_value="user-123"):
            yield mock


def test_get_all_cases_queries_by_user_id(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value \
        .order.return_value.execute.return_value.data = [{"id": "c1"}]

    from lib.db import get_all_cases
    result = get_all_cases()

    mock_client.table.assert_called_with("cases")
    assert result == [{"id": "c1"}]


def test_save_case_injects_user_id(mock_client):
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "c1", "user_id": "user-123", "court_code": "DEL001"}
    ]

    from lib.db import save_case
    result = save_case({"court_code": "DEL001"})

    call_args = mock_client.table.return_value.insert.call_args[0][0]
    assert call_args["user_id"] == "user-123"
    assert call_args["court_code"] == "DEL001"
    assert result["id"] == "c1"


def test_get_orders_for_case_queries_by_case_id(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value \
        .order.return_value.execute.return_value.data = []

    from lib.db import get_orders_for_case
    get_orders_for_case("case-123")

    mock_client.table.assert_called_with("orders")


def test_get_hearing_history_queries_by_case_id(mock_client):
    mock_client.table.return_value.select.return_value.eq.return_value \
        .order.return_value.execute.return_value.data = []

    from lib.db import get_hearing_history_for_case
    get_hearing_history_for_case("case-123")

    mock_client.table.assert_called_with("hearing_history")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_db.py -v
```

Expected: `ImportError` — `lib.db` does not exist yet.

- [ ] **Step 3: Implement the DB layer**

Create `lib/db.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_db.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add lib/db.py tests/test_db.py
git commit -m "feat: database query layer for cases, orders, and hearing history"
```

---

## Task 7: Main App Entry Point

**Files:**
- Create: `app.py`

- [ ] **Step 1: Implement app.py**

Create `app.py`:

```python
import streamlit as st
from lib.auth import is_authenticated, render_login_page, logout, get_user_email

st.set_page_config(
    page_title="Legal Dashboard",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
```

- [ ] **Step 2: Verify app starts**

```bash
streamlit run app.py
```

Expected: Browser opens at `http://localhost:8501` showing the login page. No errors in terminal.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: main app entry point with auth guard and sidebar"
```

---

## Task 8: Dashboard Page

**Files:**
- Create: `pages/1_Dashboard.py`

- [ ] **Step 1: Implement the Dashboard page**

Create `pages/1_Dashboard.py`:

```python
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
```

- [ ] **Step 2: Verify it renders**

```bash
streamlit run app.py
```

Navigate to Dashboard in the sidebar. With no cases it should show the empty state info message.

- [ ] **Step 3: Commit**

```bash
git add pages/1_Dashboard.py
git commit -m "feat: dashboard page with metrics, charts, and upcoming hearings"
```

---

## Task 9: My Cases Page

**Files:**
- Create: `pages/2_My_Cases.py`

- [ ] **Step 1: Implement My Cases page**

Create `pages/2_My_Cases.py`:

```python
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
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
```

- [ ] **Step 2: Verify it renders**

```bash
streamlit run app.py
```

Navigate to My Cases. With no cases it shows the empty state. With cases it shows the list.

- [ ] **Step 3: Commit**

```bash
git add pages/2_My_Cases.py
git commit -m "feat: my cases page with filters, refresh all, and case list"
```

---

## Task 10: Add New Case Page

**Files:**
- Create: `pages/3_Add_New_Case.py`

- [ ] **Step 1: Implement Add New Case page**

Create `pages/3_Add_New_Case.py`:

```python
import streamlit as st
from datetime import datetime, timezone
from lib.auth import is_authenticated, render_login_page
from lib.db import save_case, upsert_hearing_history
from lib.ecourts_client import EcourtsClient, CaseSearchResult

if not is_authenticated():
    render_login_page()
    st.stop()

st.title("Add New Case")

# ── Step 1: Search form ───────────────────────────────────────────────────
st.subheader("Step 1: Search for the case on eCourts")

with st.form("case_search"):
    col1, col2 = st.columns(2)
    with col1:
        court_code = st.text_input("Court Code", placeholder="e.g. DEL001")
        case_number = st.text_input("Case Number", placeholder="e.g. 422")
    with col2:
        case_type = st.text_input("Case Type", placeholder="e.g. OMP(COMM)")
        year = st.number_input("Year", min_value=1990, max_value=2030, value=2025, step=1)
    submitted = st.form_submit_button("Search eCourts", type="primary", use_container_width=True)

if submitted:
    if not all([court_code, case_type, case_number, year]):
        st.error("All four fields are required.")
        st.stop()
    try:
        api = EcourtsClient()
        result: CaseSearchResult | None = api.search_case(court_code, case_type, str(case_number), int(year))
        if result is None:
            st.warning("No case found for those details. Please check the court code, case type, number, and year.")
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
            "year": result.year,
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

            # Fetch and store hearing history
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
```

- [ ] **Step 2: Verify the form renders**

```bash
streamlit run app.py
```

Navigate to Add New Case. The search form should appear with all four fields. Submitting without an API key will raise an error (expected — no key yet).

- [ ] **Step 3: Commit**

```bash
git add pages/3_Add_New_Case.py
git commit -m "feat: add new case page with api search and save flow"
```

---

## Task 11: Case Detail Page

**Files:**
- Create: `pages/4_Case_Detail.py`

- [ ] **Step 1: Implement Case Detail page**

Create `pages/4_Case_Detail.py`:

```python
import streamlit as st
import pandas as pd
from lib.auth import is_authenticated, render_login_page
from lib.db import (
    get_case_by_id, update_case, get_orders_for_case,
    upsert_orders, update_order_summary, get_hearing_history_for_case,
    upsert_hearing_history,
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

action_col1, action_col2 = st.columns([1, 5])
with action_col1:
    if st.button("🔄 Refresh Case"):
        try:
            api = EcourtsClient()
            from lib.db import update_case_from_refresh
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
            st.success("Refreshed.")
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
    if st.button("Fetch Orders from eCourts (₹1.25)"):
        try:
            api = EcourtsClient()
            orders_from_api = api.get_orders(
                case["court_code"], case["case_type"], case["case_number"], case["year"]
            )
            upsert_orders(
                case_id,
                [{"order_date": o.order_date, "order_number": o.order_number, "pdf_url": o.pdf_url}
                 for o in orders_from_api],
            )
            st.success(f"Fetched {len(orders_from_api)} orders.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to fetch orders: {e}")

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
                            s = api.get_order_summary(order["order_number"], case["court_code"])
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
```

- [ ] **Step 2: Verify the page renders**

```bash
streamlit run app.py
```

Navigate to My Cases, click "View Details" on any case. The Case Detail page should load with tabs.

- [ ] **Step 3: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add pages/4_Case_Detail.py
git commit -m "feat: case detail page with hearings, orders, and notes tabs"
```

---

## Task 12: End-to-End Smoke Test

No new files — this is a manual verification checklist before calling the prototype done.

- [ ] **Step 1: Verify login flow**

1. Open `http://localhost:8501`
2. Confirm login page appears (not the dashboard)
3. Sign in with email/password
4. Confirm redirect to Dashboard

- [ ] **Step 2: Verify Add New Case flow** (requires API key in `.env`)

1. Navigate to Add New Case
2. Enter a valid court code, case type, case number, and year
3. Click Search — confirm API result preview appears
4. Fill in client name and notes, click Save
5. Confirm redirect to Case Detail page
6. Confirm case data is visible

- [ ] **Step 3: Verify Dashboard reflects saved cases**

1. Navigate to Dashboard
2. Confirm metric cards show updated counts
3. Confirm charts show the saved case's court and status
4. If NDOH is within 14 days, confirm it appears in Upcoming Hearings

- [ ] **Step 4: Verify My Cases filters**

1. Navigate to My Cases
2. Filter by client name — confirm only matching cases show
3. Clear filter — confirm all cases return

- [ ] **Step 5: Verify Notes save**

1. Open a Case Detail page
2. Go to Notes tab
3. Edit background notes and action items
4. Click Save
5. Refresh the page — confirm notes persisted

- [ ] **Step 6: Verify sign out**

1. Click Sign Out in sidebar
2. Confirm redirect to login page
3. Confirm navigating to any page shows login, not case data

- [ ] **Step 7: Final commit**

```bash
git add .
git commit -m "chore: complete legal dashboard prototype"
```

---

## API Field Name Note

The eCourts API field names in `lib/ecourts_client.py` are based on reasonable conventions from the public documentation. Once you have the API key and can view the actual Postman collection or live responses, verify these mappings in `search_case()`, `get_orders()`, and `get_hearing_history()` and update the field names if they differ. All mappings are isolated to those three methods — nowhere else in the codebase reads raw API responses.
