-- Add CNR (Case Number Record) column to cases table
-- CNR is the unique 16-character identifier used by the eCourts API
alter table cases add column if not exists cnr text;
create index if not exists idx_cases_cnr on cases(cnr);
