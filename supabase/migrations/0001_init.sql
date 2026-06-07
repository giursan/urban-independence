-- Companion — initial schema
-- Postgres + pgvector: profiles, conversations, long-term memory, mood/safety
-- logging, wellbeing snapshots, and consented expiring share links.
-- Row Level Security is enabled on every table and scoped to the calling user
-- (auth.uid()); two RPCs (match_memories, resolve_shared_report) carry the
-- vector search and the public, token-based share resolution.

create extension if not exists vector;
create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- profiles: one row per auth user, auto-created on signup (trigger below)
-- ---------------------------------------------------------------------------
create table public.profiles (
  id             uuid primary key references auth.users (id) on delete cascade,
  display_name   text,
  preferred_name text,
  locale         text        not null default 'en',
  interests      text[]      not null default '{}',
  life_context   jsonb       not null default '{}'::jsonb,
  onboarded      boolean     not null default false,
  created_at     timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- conversations + messages
-- ---------------------------------------------------------------------------
create table public.conversations (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid        not null references auth.users (id) on delete cascade,
  mode       text        not null default 'companion',
  started_at timestamptz not null default now()
);
create index conversations_user_started_idx
  on public.conversations (user_id, started_at desc);

create table public.messages (
  id              uuid primary key default gen_random_uuid(),
  conversation_id uuid        not null references public.conversations (id) on delete cascade,
  user_id         uuid        not null references auth.users (id) on delete cascade,
  role            text        not null check (role in ('user', 'assistant', 'system')),
  content         text        not null,
  created_at      timestamptz not null default now()
);
create index messages_conversation_idx on public.messages (conversation_id, created_at);
create index messages_user_created_idx on public.messages (user_id, created_at);

-- ---------------------------------------------------------------------------
-- memories: OpenAI embeddings (text-embedding-3-small → 1536 dims) for recall
-- ---------------------------------------------------------------------------
create table public.memories (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid        not null references auth.users (id) on delete cascade,
  content    text        not null,
  kind       text        not null default 'fact',
  salience   real        not null default 0.6,
  embedding  vector(1536),
  created_at timestamptz not null default now()
);
create index memories_user_idx on public.memories (user_id);
create index memories_embedding_idx
  on public.memories using hnsw (embedding vector_cosine_ops);

-- ---------------------------------------------------------------------------
-- mood_logs + safety_events
-- ---------------------------------------------------------------------------
create table public.mood_logs (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid        not null references auth.users (id) on delete cascade,
  conversation_id uuid        references public.conversations (id) on delete set null,
  score           int         not null check (score between 1 and 10),
  label           text        not null default '',
  note            text        not null default '',
  created_at      timestamptz not null default now()
);
create index mood_logs_user_created_idx on public.mood_logs (user_id, created_at);

create table public.safety_events (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid        not null references auth.users (id) on delete cascade,
  conversation_id uuid        references public.conversations (id) on delete set null,
  severity        text        not null,
  category        text        not null,
  excerpt         text        not null default '',
  created_at      timestamptz not null default now()
);
create index safety_events_user_created_idx on public.safety_events (user_id, created_at);

-- ---------------------------------------------------------------------------
-- wellbeing_snapshots, reports, and expiring share links
-- ---------------------------------------------------------------------------
create table public.wellbeing_snapshots (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid        not null references auth.users (id) on delete cascade,
  period_start  timestamptz not null,
  period_end    timestamptz not null,
  payload       jsonb       not null,
  model_version text,
  confidence    real,
  created_at    timestamptz not null default now()
);
create index wellbeing_snapshots_user_created_idx
  on public.wellbeing_snapshots (user_id, created_at desc);

create table public.reports (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid        not null references auth.users (id) on delete cascade,
  snapshot_id uuid        not null references public.wellbeing_snapshots (id) on delete cascade,
  created_at  timestamptz not null default now()
);
create index reports_user_idx on public.reports (user_id);

create table public.report_shares (
  id              uuid primary key default gen_random_uuid(),
  report_id       uuid        not null references public.reports (id) on delete cascade,
  user_id         uuid        not null references auth.users (id) on delete cascade,
  token           text        not null unique default encode(gen_random_bytes(24), 'hex'),
  recipient_label text,
  expires_at      timestamptz not null,
  revoked         boolean     not null default false,
  created_at      timestamptz not null default now()
);
create index report_shares_token_idx on public.report_shares (token);

-- ---------------------------------------------------------------------------
-- Auto-create a profile row when a new auth user signs up
-- ---------------------------------------------------------------------------
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, display_name)
  values (
    new.id,
    coalesce(
      new.raw_user_meta_data ->> 'full_name',
      new.raw_user_meta_data ->> 'name',
      split_part(new.email, '@', 1)
    )
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------------------
-- match_memories: cosine-nearest memories for the calling user.
-- SECURITY INVOKER so the memories RLS policy applies; query_embedding is sent
-- as a JSON-stringified array and cast to vector by PostgREST.
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

-- ---------------------------------------------------------------------------
-- resolve_shared_report: public, token-based resolution of a shared report.
-- SECURITY DEFINER so it can read across tables for an unauthenticated viewer,
-- but only returns active (not revoked, not expired) shares.
-- ---------------------------------------------------------------------------
create or replace function public.resolve_shared_report(share_token text)
returns table (
  snapshot   jsonb,
  created_at timestamptz
)
language sql
stable
security definer
set search_path = public
as $$
  select
    w.payload  as snapshot,
    w.created_at
  from public.report_shares s
  join public.reports r              on r.id = s.report_id
  join public.wellbeing_snapshots w  on w.id = r.snapshot_id
  where s.token = share_token
    and s.revoked = false
    and s.expires_at > now()
  limit 1;
$$;

-- ---------------------------------------------------------------------------
-- Row Level Security: every table is owner-scoped to auth.uid().
-- The service-role key (used only by the public share endpoint) bypasses RLS.
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

create policy profiles_self on public.profiles
  for all using (id = auth.uid()) with check (id = auth.uid());

create policy conversations_owner on public.conversations
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy messages_owner on public.messages
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy memories_owner on public.memories
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy mood_logs_owner on public.mood_logs
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy safety_events_owner on public.safety_events
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy wellbeing_snapshots_owner on public.wellbeing_snapshots
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy reports_owner on public.reports
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy report_shares_owner on public.report_shares
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- ---------------------------------------------------------------------------
-- Grants for PostgREST roles
-- ---------------------------------------------------------------------------
grant execute on function public.match_memories(vector, int) to authenticated;
grant execute on function public.resolve_shared_report(text) to anon, authenticated, service_role;
