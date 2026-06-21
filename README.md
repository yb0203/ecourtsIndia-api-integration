# Legal Dashboard — eCourts India Integration

A Streamlit app for solo lawyers to track Indian court cases. It fetches case
data from the [eCourts India API](https://ecourtsindia.com) by CNR, stores cases
in Supabase (Postgres + Auth, with Row Level Security), and shows a dashboard,
case list, and per-case detail with hearings, orders, and notes.

## Stack

- **Streamlit** — UI (`app.py` + `pages/`)
- **Supabase** — Postgres database + Auth, isolated per user via RLS
- **eCourts India API** — source of case/hearing/order data (`lib/ecourts_client.py`)

## Prerequisites

- Python 3.11+
- A Supabase project (already provisioned — see `.env.example`)
- An eCourts India API key (obtain privately — see [Configuration](#configuration))

## Setup

```bash
# 1. clone
git clone https://github.com/yb0203/ecourtsIndia-api-integration
cd ecourtsIndia-api-integration

# 2. create a virtualenv and install deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. configure environment
cp .env.example .env
#    then edit .env and add the eCourts API key (see below)

# 4. run
streamlit run app.py
```

The app opens at http://localhost:8501.

## Configuration

Environment variables (see `.env.example`):

| Variable | What it is | Shareable? |
|----------|-----------|------------|
| `SUPABASE_URL` | Supabase project URL | Yes — pre-filled |
| `SUPABASE_ANON_KEY` | Supabase **publishable** key, protected by RLS | Yes — pre-filled |
| `ECOURTS_API_KEY` | Live, credit-billed eCourts key (`eci_live_…`) | **No — keep secret** |
| `APP_URL` | Base URL used for the Google OAuth redirect | Yes |

> **Security:** Never commit a real `ECOURTS_API_KEY`. It is a live, credit-billed
> secret — committing it would expose it in git history permanently and let anyone
> burn the account's credits. Get it from the team via a password manager or DM and
> put it only in your local (gitignored) `.env`. The Supabase publishable key is
> safe to share because Row Level Security, not the key, is what protects the data.

## Database

Schema lives in `supabase/migrations/`. Apply it to a fresh project with the
Supabase CLI:

```bash
supabase db push
```

It creates `cases`, `orders`, and `hearing_history`, all with RLS policies that
scope every row to its owner (`auth.uid() = user_id`). The existing project in
`.env.example` already has these applied.

## Authentication & data isolation

Users sign in with email/password or Google OAuth (Supabase Auth). Every database
request is made with the signed-in user's JWT, so Postgres sees `auth.uid()` and
the RLS policies return only that user's rows. The Supabase client is created
**per Streamlit session** (never as a process-global singleton), so one user's
token can never leak into another session sharing the server process
(`lib/supabase_client.py`).

## Running tests

```bash
source .venv/bin/activate
pip install pytest pytest-mock
pytest -q
```

## Project structure

```
app.py                       # entry point + auth gate + sidebar
lib/
  auth.py                    # Supabase Auth: login, signup, Google OAuth, logout
  supabase_client.py         # per-session, JWT-authenticated Supabase client
  db.py                      # cases / orders / hearing_history queries
  ecourts_client.py          # eCourts India API client (by CNR)
pages/
  1_Dashboard.py             # metrics overview
  2_My_Cases.py              # case list with filters + refresh
  3_Add_New_Case.py          # add a case (API search or manual entry)
  4_Case_Detail.py           # hearings / orders / notes tabs
supabase/migrations/         # database schema + RLS policies
tests/                       # pytest unit tests
```
