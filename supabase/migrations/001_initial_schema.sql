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
