-- Phone-call identity verification.
--
-- The voice companion must establish WHO is calling before exposing a person's
-- private profile and memory. A known caller number identifies the user
-- outright; an unknown number is challenged for first+last name and a security
-- question whose answer is stored only as a salted hash (see app/identity.py).

-- ---------------------------------------------------------------------------
-- caller_phone_numbers: maps a caller's number to a user. A user may have more
-- than one number; a number belongs to exactly one user. New numbers are added
-- here after a successful name+question verification so repeat calls skip the
-- challenge.
-- ---------------------------------------------------------------------------
create table public.caller_phone_numbers (
  phone      text        primary key,           -- digits only, see normalize_phone()
  user_id    uuid        not null references auth.users (id) on delete cascade,
  verified   boolean     not null default false,
  created_at timestamptz not null default now()
);
create index caller_phone_numbers_user_idx on public.caller_phone_numbers (user_id);

-- ---------------------------------------------------------------------------
-- security_questions: per-user challenge questions. Answers are never stored in
-- the clear — only answer_hash. created_by records provenance ('onboarding' for
-- the person, or a caregiver label when a relative adds one).
-- ---------------------------------------------------------------------------
create table public.security_questions (
  id          uuid        primary key default gen_random_uuid(),
  user_id     uuid        not null references auth.users (id) on delete cascade,
  question    text        not null,
  answer_hash text        not null,
  created_by  text        not null default 'onboarding',
  created_at  timestamptz not null default now()
);
create index security_questions_user_idx on public.security_questions (user_id);

-- ---------------------------------------------------------------------------
-- call_sessions: per-call verification state, keyed by Twilio CallSid. Written
-- only by the voice webhook (which runs server-side with no JWT), so it carries
-- no owner policy — RLS stays on with no policy, leaving it service-role only.
-- Stages: AWAIT_NAME, AWAIT_SECURITY_ANSWER, VERIFIED, FAILED.
-- ---------------------------------------------------------------------------
create table public.call_sessions (
  call_sid          text        primary key,
  stage             text        not null default 'AWAIT_NAME',
  candidate_user_id uuid,
  verified_user_id  uuid,
  attempts          int         not null default 0,
  updated_at        timestamptz not null default now()
);

-- RLS: owner policies mirror 0001 (disabled for dev in the 0006 sibling).
alter table public.caller_phone_numbers enable row level security;
create policy caller_phone_numbers_owner on public.caller_phone_numbers
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

alter table public.security_questions enable row level security;
create policy security_questions_owner on public.security_questions
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

alter table public.call_sessions enable row level security;
