-- Dodo Lounge: Supabase schema. Safe to run more than once.
create extension if not exists btree_gist with schema extensions;

-- ---------------------------------------------------------------- profiles
create table if not exists public.profiles (
  id         uuid primary key references auth.users (id) on delete cascade,
  email      text,
  full_name  text,
  phone      text,
  role       text not null default 'client' check (role in ('client', 'staff')),
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------- bookings
create table if not exists public.bookings (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references public.profiles (id) on delete cascade,
  service    text not null,
  staff      text not null check (staff in ('dodo', 'jana', 'sarah')),
  start_at   timestamptz not null,
  end_at     timestamptz not null,
  name       text not null,
  phone      text not null,
  note       text not null default '',
  status     text not null default 'unsent' check (status in ('unsent', 'pending', 'confirmed', 'cancelled', 'done', 'expired')),
  created_at timestamptz not null default now(),
  constraint bookings_time_order check (end_at > start_at),
  -- the database itself refuses two live bookings that overlap for the same person
  constraint bookings_no_overlap exclude using gist (
    staff with =, tstzrange(start_at, end_at) with &&
  ) where (status in ('unsent', 'pending', 'confirmed'))
);
-- Website bookings start "unsent" (hidden from staff, held 15 min) until the client taps Send on WhatsApp.
-- Safety net: a booking made by a client account can never be created as confirmed (or pending).
create or replace function public.bookings_client_starts_unsent() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if coalesce((select p.role from public.profiles p where p.id = new.user_id), 'client') <> 'staff' then
    new.status := 'unsent';
  end if;
  return new;
end $$;
revoke all on function public.bookings_client_starts_unsent() from public, anon, authenticated;
drop trigger if exists bookings_client_starts_unsent on public.bookings;
create trigger bookings_client_starts_unsent before insert on public.bookings
  for each row execute function public.bookings_client_starts_unsent();
create index if not exists bookings_user_idx  on public.bookings (user_id);
create index if not exists bookings_start_idx on public.bookings (start_at);

-- ---------------------------------------------------------------- orders
create table if not exists public.orders (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references public.profiles (id) on delete cascade,
  name       text not null,
  phone      text not null,
  address    text not null,
  note       text not null default '',
  items      jsonb not null,
  total      integer not null check (total >= 0),
  status     text not null default 'new' check (status in ('new', 'delivered', 'cancelled')),
  created_at timestamptz not null default now()
);
create index if not exists orders_user_idx on public.orders (user_id);

-- ---------------------------------------------------------------- security
-- The website server uses the service-role key (bypasses RLS). Browsers get nothing
-- except reading their own rows, should a client-side feature ever need it.
alter table public.profiles enable row level security;
alter table public.bookings enable row level security;
alter table public.orders   enable row level security;

drop policy if exists "own profile"  on public.profiles;
drop policy if exists "own bookings" on public.bookings;
drop policy if exists "own orders"   on public.orders;
create policy "own profile"  on public.profiles for select to authenticated using ((select auth.uid()) = id);
create policy "own bookings" on public.bookings for select to authenticated using ((select auth.uid()) = user_id);
create policy "own orders"   on public.orders   for select to authenticated using ((select auth.uid()) = user_id);

-- ---------------------------------------------------------------- Data API access
-- The website server uses the service role. Signed-in users may only read their own rows (RLS above).
grant usage on schema public to service_role, authenticated;
grant select, insert, update, delete on public.profiles, public.bookings, public.orders to service_role;
grant usage, select on all sequences in schema public to service_role;
grant select on public.profiles, public.bookings, public.orders to authenticated;
revoke all on public.profiles, public.bookings, public.orders from anon;
