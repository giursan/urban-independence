-- DEV / TEST ONLY — removes authentication so the app runs without sign-in.
--
-- This tears down the security model from 0001_init.sql:
--   * disables Row Level Security on every table,
--   * drops the foreign keys to auth.users (so a synthetic dev user id is valid),
--   * makes match_memories ignore auth.uid() (there is no JWT),
--   * seeds one fixed dev user profile.
--
-- To restore real auth, drop this migration and re-apply 0001 (or re-enable RLS,
-- re-add the auth.users FKs, and restore the auth.uid() filter below).

-- Fixed dev user — must match DEV_USER_ID in apps/api and apps/web.
-- 00000000-0000-0000-0000-000000000001

-- ---------------------------------------------------------------------------
-- Drop foreign keys to auth.users (the dev user does not exist in auth.users)
-- ---------------------------------------------------------------------------
alter table public.profiles            drop constraint if exists profiles_id_fkey;
alter table public.conversations       drop constraint if exists conversations_user_id_fkey;
alter table public.messages            drop constraint if exists messages_user_id_fkey;
alter table public.memories            drop constraint if exists memories_user_id_fkey;
alter table public.mood_logs           drop constraint if exists mood_logs_user_id_fkey;
alter table public.safety_events       drop constraint if exists safety_events_user_id_fkey;
alter table public.wellbeing_snapshots drop constraint if exists wellbeing_snapshots_user_id_fkey;
alter table public.reports             drop constraint if exists reports_user_id_fkey;
alter table public.report_shares       drop constraint if exists report_shares_user_id_fkey;

-- ---------------------------------------------------------------------------
-- Disable Row Level Security everywhere (no JWT, so policies would block all)
-- ---------------------------------------------------------------------------
alter table public.profiles            disable row level security;
alter table public.conversations       disable row level security;
alter table public.messages            disable row level security;
alter table public.memories            disable row level security;
alter table public.mood_logs           disable row level security;
alter table public.safety_events       disable row level security;
alter table public.wellbeing_snapshots disable row level security;
alter table public.reports             disable row level security;
alter table public.report_shares       disable row level security;

-- Make sure the anon/authenticated PostgREST roles can read/write directly
-- (the web app talks to Supabase with the anon key and no session).
grant all on all tables in schema public to anon, authenticated;

-- ---------------------------------------------------------------------------
-- match_memories without the auth.uid() scope (single dev user, no JWT)
-- ---------------------------------------------------------------------------
create or replace function public.match_memories(
  query_embedding vector(1536),
  match_count int default 5
)
returns table (
  id         uuid,
  content    text,
  kind       text,
  salience   real,
  similarity float
)
language sql
stable
as $$
  select
    m.id,
    m.content,
    m.kind,
    m.salience,
    1 - (m.embedding <=> query_embedding) as similarity
  from public.memories m
  where m.embedding is not null
  order by m.embedding <=> query_embedding
  limit greatest(match_count, 1);
$$;

grant execute on function public.match_memories(vector, int) to anon, authenticated;

-- ---------------------------------------------------------------------------
-- Seed the fixed dev user profile (onboarded so the app skips onboarding)
-- ---------------------------------------------------------------------------
insert into public.profiles (id, preferred_name, onboarded)
values ('00000000-0000-0000-0000-000000000001', 'Friend', true)
on conflict (id) do nothing;
