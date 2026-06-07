-- DEV / TEST ONLY — match 0002's auth-disabled behavior for the identity tables.

alter table public.caller_phone_numbers drop constraint if exists caller_phone_numbers_user_id_fkey;
alter table public.security_questions   drop constraint if exists security_questions_user_id_fkey;

alter table public.caller_phone_numbers disable row level security;
alter table public.security_questions   disable row level security;
alter table public.call_sessions        disable row level security;

grant all on public.caller_phone_numbers to anon, authenticated;
grant all on public.security_questions to anon, authenticated;
grant all on public.call_sessions to anon, authenticated;

-- Seed a phone number for the fixed dev user so the known-number path works out
-- of the box. Replace with your own number to test the straight-through call.
-- (Security questions are created via onboarding / the care page so their
-- answer hashes match app/identity.py's secret — we do not seed a hash here.)
insert into public.caller_phone_numbers (phone, user_id, verified)
values ('15555550100', '00000000-0000-0000-0000-000000000001', true)
on conflict (phone) do nothing;
