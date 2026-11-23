-- MZ SITEHUB : table des TSS et CCT du calendrier
-- A coller dans le SQL Editor de Supabase puis cliquer sur "Run".
-- Peut etre lance plusieurs fois sans danger.

create table if not exists site_visits (
    id uuid primary key default gen_random_uuid(),
    visit_type text not null check (visit_type in ('TSS', 'CCT')),
    visit_date date not null,
    site_id uuid references sites(id),
    site_code text not null,
    location text,
    bet_name text,
    radio_engineer_name text,
    civil_work_name text,
    transmission_name text,
    negotiator_name text,
    observation text,
    created_by uuid references users(id),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_site_visits_date on site_visits (visit_date);
create index if not exists idx_site_visits_site on site_visits (site_id);
