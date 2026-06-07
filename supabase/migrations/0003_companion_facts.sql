create table public.companion_facts (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid        not null references auth.users (id) on delete cascade,
  category   text        not null default 'personal',
  title      text        not null,
  content    text        not null,
  tags       text[]      not null default '{}',
  importance int         not null default 3 check (importance between 1 and 5),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index companion_facts_user_updated_idx
  on public.companion_facts (user_id, updated_at desc);

create or replace function public.touch_companion_fact_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists companion_facts_touch_updated_at on public.companion_facts;
create trigger companion_facts_touch_updated_at
  before update on public.companion_facts
  for each row execute function public.touch_companion_fact_updated_at();

alter table public.companion_facts enable row level security;

create policy companion_facts_owner on public.companion_facts
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
