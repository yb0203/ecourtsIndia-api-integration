# Legal Dashboard — Design Spec
**Date:** 2026-06-20  
**Stack:** Python · Streamlit · Supabase · eCourts India API (ecourtsindia.com)

---

## 1. Problem

A lawyer managing ~25 active cases across a dozen different courts currently tracks everything in a manually-updated PDF spreadsheet. The sheet captures case numbers, forums, parties, next hearing dates, remarks, and statuses — but it requires manual updates, has no live data, and gives no at-a-glance picture of the overall case load. The goal is to replace this with a live dashboard that fetches real case data from the eCourts India API, stores it per lawyer, and lets the lawyer annotate cases with their own notes.

---

## 2. Scope

This is a **single-client prototype** for one lawyer, built to validate the workflow before scaling. The prototype covers:

- Authentication (Google OAuth + email/password via Supabase Auth)
- Case lookup via the ecourtsindia.com REST API
- Saving and tracking cases linked to a logged-in lawyer
- Manual annotation fields (notes, action items, client, counsel, amount)
- Case detail view with orders and hearing history
- A home dashboard with summary metrics and charts
- Refresh of live case data on demand

**Out of scope for this prototype:**
- Multi-lawyer firm accounts / shared case pools
- Notification / alerting system for hearing date changes
- PDF import of the existing spreadsheet
- Cases not on eCourts (arbitrations, MSME councils, NCLT/NCLAT) — these forums are not in the eCourts API

---

## 3. API — ecourtsindia.com

There is no official government REST API for eCourts India. The ecourtsindia.com commercial API is the most reliable third-party option, offering 11 structured endpoints with per-request billing.

**Endpoints used in this project:**

| Endpoint | Cost | Purpose |
|---|---|---|
| GET /api/partner/search | ₹0.20/req | Search by court code, case type, case number, year |
| GET /api/partner/case | ₹0.50/req | Full case detail — parties, judge, status, NDOH |
| POST /api/partner/refresh | ₹0.05/req | Refresh a saved case's latest status and hearing date |
| GET /api/partner/orders | ₹1.25/req | List of orders with PDF links |
| GET /api/partner/order-summary | ₹2.50/req | Order with AI-generated plain-language summary |
| GET /api/partner/court-structure | Free | Court codes and hierarchy |
| GET /api/partner/enums | Free | Valid case types per court |

**Authentication:** API key stored as a server-side environment variable (`ECOURTS_API_KEY`). Never exposed to the browser or logged-in users.

**Key constraint:** The API covers High Courts, Commercial Courts, and District Courts only. Cases in arbitration, NCLT, NCLAT, MSME councils, and state tribunals cannot be fetched and are out of scope for this prototype.

---

## 4. Data Model

Three tables in Supabase. All tables are protected by Row Level Security (RLS) policies that scope every query to `auth.uid() = user_id`.

### 4.1 `cases`

The core table. Every saved case belongs to exactly one lawyer.

| Column | Type | Source |
|---|---|---|
| `id` | uuid (PK) | auto |
| `user_id` | uuid (FK → auth.users) | Supabase Auth |
| `court_code` | text | user input (API lookup key) |
| `case_type` | text | user input (API lookup key) |
| `case_number` | text | user input (API lookup key) |
| `year` | integer | user input (API lookup key) |
| `court_name` | text | API |
| `state` | text | API |
| `petitioner` | text | API |
| `respondent` | text | API |
| `judge` | text | API |
| `filing_date` | date | API |
| `next_hearing_date` | date | API |
| `court_status` | text | API (official court status) |
| `client_name` | text | manual |
| `amount_at_stake` | numeric | manual (e.g. 240000000) |
| `local_counsel` | text | manual |
| `background_notes` | text | manual (permanent context) |
| `action_items` | text | manual (what needs to happen next) |
| `lawyer_status` | text | manual (Active / Pending-TBF / Disposed) |
| `last_refreshed_at` | timestamptz | system |
| `created_at` | timestamptz | auto |

### 4.2 `orders`

One case has many orders. Populated when the lawyer fetches orders for a case.

| Column | Type | Source |
|---|---|---|
| `id` | uuid (PK) | auto |
| `case_id` | uuid (FK → cases.id) | system |
| `user_id` | uuid (FK → auth.users) | Supabase Auth (for RLS) |
| `order_date` | date | API |
| `order_number` | text | API |
| `pdf_url` | text | API |
| `ai_summary` | text | API (order-summary endpoint) |
| `created_at` | timestamptz | auto |

### 4.3 `hearing_history`

One case has many past hearing dates. Populated on case save and each refresh.

| Column | Type | Source |
|---|---|---|
| `id` | uuid (PK) | auto |
| `case_id` | uuid (FK → cases.id) | system |
| `user_id` | uuid (FK → auth.users) | Supabase Auth (for RLS) |
| `hearing_date` | date | API |
| `purpose` | text | API |
| `outcome` | text | API |
| `created_at` | timestamptz | auto |

### 4.4 Relationships

```
auth.users
  └── id
        │
        ├── cases.user_id          (one lawyer → many cases)
        │     └── cases.id
        │           ├── orders.case_id     (one case → many orders)
        │           └── hearing_history.case_id  (one case → many hearings)
        ├── orders.user_id         (for RLS enforcement)
        └── hearing_history.user_id (for RLS enforcement)
```

---

## 5. Application Pages

Streamlit app with a sidebar navigation. The sidebar shows the logged-in lawyer's name and a Sign Out button on every page after login.

### Page 0 — Login

The entry point for unauthenticated users. Shows:
- App name and tagline
- "Sign in with Google" button (Supabase OAuth)
- Email + password form as fallback
- On success: session token stored in `st.session_state`, redirect to Dashboard

### Page 1 — Dashboard (Home)

**Top row — four metric cards:**
- Total Active Cases
- Hearings This Week
- Hearings This Month
- Disposed Cases

**Middle row — two charts side by side:**
- Bar chart: Cases by Forum (Commercial Court, High Court, District Court, etc.)
- Donut chart: Cases by Lawyer Status (Active, Pending-TBF, Disposed)

**Bottom — Upcoming Hearings table:**
- All cases with `next_hearing_date` in the next 14 days
- Columns: Case No., Court, Parties, Client, NDOH, Status
- Sorted ascending by date

### Page 2 — My Cases

Full list of all saved cases for the logged-in lawyer.

**Filters (sidebar or top bar):**
- Client name
- Forum / court
- Lawyer status
- Date range for NDOH

**Table columns:**
- Case No.
- Court
- Petitioner vs Respondent
- Client
- NDOH
- Lawyer Status
- Last Refreshed

**Actions:**
- Click any row → opens Case Detail (Page 3)
- "Refresh All" button → calls the refresh endpoint for every case and updates `next_hearing_date`, `court_status`, and `last_refreshed_at`

### Page 3 — Case Detail

Opened by clicking a row in My Cases. Laid out in two sections.

**Header section (from `cases` table):**
- Case number, court name, state
- Petitioner vs Respondent
- Judge, filing date, NDOH
- Official court status badge
- Client name, amount at stake, local counsel
- "Refresh Case" button and "Edit Notes" button

**Tabbed section below:**

**Tab 1 — Hearings** (from `hearing_history` WHERE `case_id = this case`)
- Timeline table: Date | Purpose | Outcome
- Sorted descending (most recent first)

**Tab 2 — Orders** (from `orders` WHERE `case_id = this case`)
- Table: Date | Order No. | AI Summary | PDF link
- "Fetch Orders" button to pull latest from API (costs ₹1.25 per order)

**Tab 3 — Notes** (editable fields from `cases` table)
- Background Notes (text area)
- Action Items (text area)
- Lawyer Status (select: Active / Pending-TBF / Disposed)
- Save button → updates Supabase

### Page 4 — Add New Case

**Step 1 — Search form:**
- Court Code (text input, with helper to browse via the free Court Structure endpoint)
- Case Type (dropdown, populated from free Enums endpoint)
- Case Number (text input)
- Year (number input)
- Search button → calls Case Search API (₹0.20)

**Step 2 — Preview result:**
- Shows fetched data: court, parties, judge, filing date, NDOH, court status
- If no result found: error message, allow re-search

**Step 3 — Add metadata (shown after successful fetch):**
- Client Name (text input)
- Amount at Stake (number input)
- Local Counsel (text input)
- Background Notes (text area)
- Action Items (text area)
- Lawyer Status (select)
- Save Case button → writes to Supabase, fetches and stores hearing history

---

## 6. Data Flow

### Adding a new case
```
User enters court code + case type + case number + year
  → App calls ecourtsindia.com /search (₹0.20)
  → API returns case details
  → App displays preview
  → User fills in manual fields and clicks Save
  → App writes one row to `cases`
  → App calls /case for full detail (₹0.50) to populate hearing history
  → App writes rows to `hearing_history`
  → Redirect to Case Detail page
```

### Refreshing a case
```
User clicks "Refresh Case" or "Refresh All"
  → App calls /refresh for each case (₹0.05 each)
  → API returns updated next_hearing_date and court_status
  → App updates `cases` row: next_hearing_date, court_status, last_refreshed_at
  → App fetches latest hearing_history and upserts new rows
  → UI re-renders with fresh data
```

### Fetching orders
```
User opens Orders tab and clicks "Fetch Orders"
  → App calls /orders for this case (₹1.25)
  → API returns list of orders with PDF URLs
  → App upserts rows into `orders` table
  → For each order, user can click "Get AI Summary" (₹2.50 each, on demand)
  → Summary written to orders.ai_summary
```

---

## 7. Authentication Flow

1. User visits app URL → Streamlit checks `st.session_state` for active session
2. No session → renders Page 0 (Login)
3. Google sign-in → Supabase OAuth redirect → callback sets session in `st.session_state`
4. All Supabase queries use the user's JWT token from the session
5. Supabase RLS policies enforce `user_id = auth.uid()` on all tables
6. Sign Out → clears `st.session_state`, returns to Login page

---

## 8. Environment Variables

```
ECOURTS_API_KEY        # ecourtsindia.com API key
SUPABASE_URL           # Supabase project URL
SUPABASE_ANON_KEY      # Supabase anon/public key (safe for client)
GOOGLE_CLIENT_ID       # Google OAuth client ID (via Supabase Auth settings)
```

---

## 9. Cost Estimate (prototype usage)

Assuming one lawyer, ~25 cases, light daily usage:

| Action | Frequency | Cost per run | Monthly est. |
|---|---|---|---|
| Add new case (search + detail) | 2/week | ₹0.70 | ₹5.60 |
| Refresh all cases | Daily | ₹1.25 (25 × ₹0.05) | ₹37.50 |
| Fetch orders (per case) | 2/week | ₹1.25 | ₹10.00 |
| AI order summaries | 4/month | ₹2.50 | ₹10.00 |
| **Total** | | | **~₹63/month** |

---

## 10. Open Questions

- Does ecourtsindia.com cover Commercial Courts (Hyderabad) and District Courts in addition to High Courts? This needs to be confirmed after getting the API key, as several MBECL cases are in those forums.
- Should the lawyer be able to manually add cases that are not on eCourts (arbitrations, NCLT) as manual-only records? Deferred to v2 but worth noting.
- Is there a need for multiple lawyers at the same firm to share cases or is full isolation always correct? Deferred to v2.
