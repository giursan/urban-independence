-- Re-enable real authentication (reverses 0002 / 0004 / 0006).
--
-- Restores the security model from 0001: foreign keys to auth.users, Row-Level
-- Security on every table (the owner policies from 0001/0003/0005 are still
-- present, just dormant), and the user-scoped match_memories. After this, each
-- request must carry a valid Supabase JWT and only sees its own rows.

-- ---------------------------------------------------------------------------
-- 1) Remove the synthetic dev user's rows so the auth.users FKs can be re-added
--    (the fixed dev id does not exist in auth.users). Child rows first.
-- ---------------------------------------------------------------------------
do $$
declare dev uuid := '00000000-0000-0000-0000-000000000001';
begin
  delete from public.messages             where user_id = dev;
  delete from public.report_shares        where user_id = dev;
  delete from public.reports              where user_id = dev;
  delete from public.wellbeing_snapshots  where user_id = dev;
  delete from public.memories             where user_id = dev;
  delete from public.mood_logs            where user_id = dev;
  delete from public.safety_events        where user_id = dev;
  delete from public.companion_facts      where user_id = dev;
  delete from public.caller_phone_numbers where user_id = dev;
  delete from public.security_questions   where user_id = dev;
  delete from public.conversations        where user_id = dev;
  delete from public.profiles             where id = dev;
end $$;

-- ---------------------------------------------------------------------------
-- 2) Re-add foreign keys to auth.users (drop-if-exists keeps this re-runnable).
-- ---------------------------------------------------------------------------
alter table public.profiles            drop constraint if exists profiles_id_fkey;
alter table public.profiles            add  constraint profiles_id_fkey
  foreign key (id) references auth.users (id) on delete cascade;

alter table public.conversations       drop constraint if exists conversations_user_id_fkey;
alter table public.conversations       add  constraint conversations_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;

alter table public.messages            drop constraint if exists messages_user_id_fkey;
alter table public.messages            add  constraint messages_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;

alter table public.memories            drop constraint if exists memories_user_id_fkey;
alter table public.memories            add  constraint memories_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;

alter table public.mood_logs           drop constraint if exists mood_logs_user_id_fkey;
alter table public.mood_logs           add  constraint mood_logs_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;

alter table public.safety_events       drop constraint if exists safety_events_user_id_fkey;
alter table public.safety_events       add  constraint safety_events_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;

alter table public.wellbeing_snapshots drop constraint if exists wellbeing_snapshots_user_id_fkey;
alter table public.wellbeing_snapshots add  constraint wellbeing_snapshots_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;

alter table public.reports             drop constraint if exists reports_user_id_fkey;
alter table public.reports             add  constraint reports_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;

alter table public.report_shares       drop constraint if exists report_shares_user_id_fkey;
alter table public.report_shares       add  constraint report_shares_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;

alter table public.companion_facts     drop constraint if exists companion_facts_user_id_fkey;
alter table public.companion_facts     add  constraint companion_facts_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;

alter table public.caller_phone_numbers drop constraint if exists caller_phone_numbers_user_id_fkey;
alter table public.caller_phone_numbers add  constraint caller_phone_numbers_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;

alter table public.security_questions  drop constraint if exists security_questions_user_id_fkey;
alter table public.security_questions  add  constraint security_questions_user_id_fkey
  foreign key (user_id) references auth.users (id) on delete cascade;

-- ---------------------------------------------------------------------------
-- 3) Re-enable Row-Level Security. Owner policies from 0001/0003/0005 reactivate.
--    call_sessions keeps RLS on with no policy → reachable only by the service
--    role (the voice webhook), never by browser clients.
-- ---------------------------------------------------------------------------
alter table public.profiles            enable row level security;
alter table public.conversations       enable row level security;
alter table public.messages            enable row level security;
alter table public.memories            enable row level security;
alter table public.mood_logs           enable row level security;
alter table public.safety_events       enable row level security;
alter table public.wellbeing_snapshots enable row level security;
alter table public.reports             enable row level security;
alter table public.report_shares       enable row level security;
alter table public.companion_facts     enable row level security;
alter table public.caller_phone_numbers enable row level security;
alter table public.security_questions  enable row level security;
alter table public.call_sessions       enable row level security;

-- ---------------------------------------------------------------------------
-- 4) Restore the user-scoped match_memories (0002 had removed the auth.uid()
--    filter while auth was disabled).
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
  where m.user_id = auth.uid()
    and m.embedding is not null
  order by m.embedding <=> query_embedding
  limit greatest(match_count, 1);
$$;
