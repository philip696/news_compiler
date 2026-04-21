# Personalized News Aggregation MVP

This repository is a runnable MVP for personalized news aggregation, discovery, and optional **WeChat Official Account** reading via a WeRead-compatible gateway.

## Project structure

| Path | Description |
|------|-------------|
| `backend/` | FastAPI API: auth, feed, topics, bookmarks, behavior, admin jobs, **WeChat / WeRead** (`/api/wechat/*`), Celery worker scaffold |
| `frontend/` | Next.js UI: feed, topics, source preferences, bookmarks, WeChat-related pages where wired |
| `test/` | Standalone prototype (Node or Python) for experimenting with the gateway without the main app |

Authoritative backend setup (Supabase, Alembic, env vars, WeChat routes) lives in **`backend/README.md`**.

## Prerequisites

- **Backend:** Python 3.11+  
- **Frontend:** Node.js 18+ and npm  
- **Production DB (optional):** PostgreSQL, e.g. [Supabase](https://supabase.com) — set `DATABASE_URL` in `backend/.env`

## Backend quickstart

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: SECRET_KEY, DATABASE_URL (for Supabase), FRONTEND_URL, PLATFORM_URL as needed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8007 --reload
```

- API base: `http://127.0.0.1:8007`  
- OpenAPI: `http://127.0.0.1:8007/docs`

For PostgreSQL / Supabase, run migrations after configuring `DATABASE_URL`:

```bash
cd backend && source .venv/bin/activate && alembic upgrade head
```

## Frontend quickstart

Point the UI at the same host and port as your API (defaults in code often assume port `8000`; this repo’s backend example uses **`8007`**).

```bash
cd frontend
npm install
echo 'NEXT_PUBLIC_API_URL=http://127.0.0.1:8007' > .env.local
npm run dev
```

App: `http://localhost:3000` (or the URL printed by Next.js).

See `frontend/.env.example` for other optional variables.

## MVP coverage

- **Auth:** JWT register / login / refresh (`/api/auth/*`)
- **Feed:** personalized feed (`/api/feed`)
- **Topics:** follow / unfollow (`/api/topics/*`)
- **Sources:** mute / prefer (`/api/source/*`)
- **Bookmarks:** create / list (`/api/articles/bookmark`, `/api/user/bookmarks`)
- **Behavior:** lightweight tracking for learning (`/api/behavior/track`)
- **Admin:** ingestion and clustering triggers (`/api/admin/ingest`, `/api/admin/cluster`, `/api/admin/rebuild`)
- **Workers:** Celery scaffold with scheduled ingestion / clustering (see `backend/README.md`)
- **WeChat / WeRead:** QR login, account pool, subscribe by article URL, sync articles — all under **`/api/wechat/*`** (requires a logged-in GEB user for most routes; see `backend/README.md`)

## Where to go next

- Full backend runbook, Supabase, and WeChat API table: **`backend/README.md`**
- Frontend-only notes: **`frontend/README.md`**
- Isolated gateway experiments: **`test/README.md`**
