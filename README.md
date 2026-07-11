# Trip App

A small web app for coordinating group trips with friends: create trips, add
members, and track flights (with itineraries, meal plans, and points of interest
planned for later). Django REST Framework backend, Vue 3 frontend, Postgres.

## Stack

| Layer     | Tech |
|-----------|------|
| Backend   | Django 5 + Django REST Framework, session-cookie auth |
| Database  | PostgreSQL 15 (local) / Neon (production) |
| Frontend  | Vue 3 (Vite, Composition API) + Pinia + Vue Router + Tailwind CSS |
| Deploy    | Single Fly.io app (Django serves the API **and** the compiled SPA, same origin) |

## Features (MVP)

- Email/password accounts (session cookies, CSRF-protected)
- Create trips; the creator becomes the owner
- Add members by email — existing users join immediately; unknown emails get a
  pending invitation that resolves automatically when that person registers
- Track flights per trip. **Multiple travelers can share one flight**, each with
  their own confirmation code and seat

## Project layout

```
backend/    Django project (config/), accounts/ app, trips/ app
frontend/   Vite + Vue 3 SPA
docker-compose.yml   local dev: postgres + backend + frontend
fly.toml    Fly.io deployment config
```

---

## Running locally

### Option A — Docker Compose (recommended)

Requires Docker.

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- API / admin: proxied through the frontend, or directly at http://localhost:8000
- Postgres: localhost:5432 (`trip` / `trip` / `trip_app`)

The backend auto-runs migrations on startup. To create an admin user:

```bash
docker compose exec backend python manage.py createsuperuser
```

### Option B — Native (uses your local Postgres 15)

**Backend:**

```bash
cd backend
cp .env.example .env            # then edit if needed
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# One-time: create the role + database referenced by DATABASE_URL
createuser trip --createdb --pwprompt   # password: trip
createdb -O trip trip_app

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver              # http://localhost:8000
```

**Frontend (separate terminal):**

```bash
cd frontend
npm install
npm run dev                             # http://localhost:5173
```

The Vite dev server proxies `/api`, `/admin`, and `/static` to the backend, so
the SPA and API share one origin and session cookies work with no CORS setup.

### Running tests

```bash
cd backend && source .venv/bin/activate
python manage.py test
```

---

## Deployment — Fly.io + Neon

The code is host-agnostic (Docker + 12-factor env vars); Fly + Neon is just the
documented target. Rough cost: **~$2–5/mo** for the always-on Fly VM; Neon
Postgres is free (0.5 GB, but scale-to-zero → ~1s cold start after idle).

### 1. Database — Neon (free, no credit card)

1. Sign up at <https://neon.com> and create a **project** (pick a region).
2. Copy the **pooled** connection string it shows you — that whole string is your
   `DATABASE_URL`.

### 2. App — Fly.io (requires a credit card after the trial)

```bash
brew install flyctl
fly auth login

# From the repo root (fly.toml lives here):
fly launch --no-deploy            # claim an app name + region; keep this fly.toml

# Match the Fly region to your Neon region for low DB latency.
fly secrets set \
  SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')" \
  DEBUG="False" \
  ALLOWED_HOSTS="<your-app>.fly.dev" \
  CSRF_TRUSTED_ORIGINS="https://<your-app>.fly.dev" \
  DATABASE_URL="<your Neon pooled connection string>"

fly deploy                        # builds the image, runs migrations, launches
```

`fly deploy` builds the multi-stage `backend/Dockerfile`: it compiles the Vue SPA,
bundles it with Django, and serves everything from one origin. The
`release_command` in `fly.toml` runs migrations on each deploy.

Create your admin user once:

```bash
fly ssh console -C "python manage.py createsuperuser"
```

---

## API overview

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/auth/csrf/` | Set the CSRF cookie |
| POST | `/api/auth/register/` | Create account + log in |
| POST | `/api/auth/login/` | Log in |
| POST | `/api/auth/logout/` | Log out |
| GET/PATCH | `/api/auth/me/` | Current user / update profile (name, dietary restrictions) |
| GET/POST | `/api/trips/` | List / create trips |
| GET/PUT/PATCH/DELETE | `/api/trips/{id}/` | Trip detail (delete = owner only) |
| GET/POST | `/api/trips/{id}/members/` | List members+invites / add member by email |
| DELETE | `/api/trips/{id}/members/{user_id}/` | Remove a member |
| GET/POST | `/api/trips/{id}/flights/` | List / create flights |
| GET/PUT/PATCH/DELETE | `/api/trips/{id}/flights/{id}/` | Flight detail |
| GET/POST | `/api/trips/{id}/accommodations/` | List / create accommodations |
| GET/PUT/PATCH/DELETE | `/api/trips/{id}/accommodations/{id}/` | Accommodation detail |

All trip-scoped endpoints require authentication and trip membership.

## Roadmap (planned)

- Itineraries (day-by-day schedule)
- Grocery lists & meal plans
- Points of interest
