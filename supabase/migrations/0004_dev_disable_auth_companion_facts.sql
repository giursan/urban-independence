-- DEV / TEST ONLY — match 0002's auth-disabled behavior for companion_facts.

alter table public.companion_facts drop constraint if exists companion_facts_user_id_fkey;
alter table public.companion_facts disable row level security;

grant all on public.companion_facts to anon, authenticated;
