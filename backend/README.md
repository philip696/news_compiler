# Backend (FastAPI)

## Prerequisites

- Python 3.11+ recommended
- For production: a PostgreSQL database (e.g. [Supabase](https://supabase.com))

## Quick start (local, SQLite)

SQLite is the default if you omit `DATABASE_URL`. Good for trying the API without Supabase.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env if you want (optional for SQLite)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8007 --reload
```

- API: `http://127.0.0.1:8007`
- OpenAPI docs: `http://127.0.0.1:8007/docs`

On first start, SQLAlchemy `create_all` creates missing tables. For a clean upgrade path (especially on PostgreSQL), use Alembic below.

## Run with Supabase (PostgreSQL)

1. In the [Supabase dashboard](https://supabase.com/dashboard), open your project → **Settings** → **Database**. Copy the **URI** (connection string). Use the **direct** connection for migrations, or the **pooler** URL for the app if you prefer (see Supabase docs for `prepared_statements` if you see related errors).

2. Put it in `backend/.env`:

```bash
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
# Or the "Transaction" / direct host URL from the dashboard
```

### Unified schema (one database)

The backend already uses **one** Postgres database for everything: auth (`users`), engagement (`bookmarks`, `likes`), and WeChat / WeRead (`weread_accounts`, `weread_feeds`, `weread_articles`). There is no separate “WeChat database” in code—only `DATABASE_URL`.

**Option A — paste SQL in Supabase (good for a fresh project)**

1. Open **SQL** → **New query** in the Supabase dashboard.
2. Paste the contents of [`sql/supabase_schema.sql`](sql/supabase_schema.sql) and run it.  
   That creates all tables, foreign keys, and indexes in `public`.

**Option B — Alembic (recommended for ongoing changes)**

```bash
cd backend && source .venv/bin/activate && alembic upgrade head
```

If you previously created `wechat_official_accounts` / `wechat_cached_articles`, remove them first (see commented `DROP` lines at the top of `supabase_schema.sql`) or let migration `a1b2c3d4e5f6` drop them when using Alembic.

3. Set the rest of your secrets (copy from `.env.example` and fill in):

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string (Supabase) |
| `SECRET_KEY` | JWT signing secret (use a long random string in production) |
| `FRONTEND_URL` | Your frontend origin (CORS); e.g. `http://localhost:3000` |
| `PLATFORM_URL` | WeRead-compatible gateway (default in `.env.example`) |
| `UPDATE_DELAY_TIME` | Seconds between history pages when syncing (default `60`) |
| `UPDATE_DELAY_MS` | Optional: override delay in milliseconds (dev only) |

Supabase does **not** require a separate “API key” in `DATABASE_URL` for SQLAlchemy: the connection string already embeds the database password. If you later add Supabase REST or Edge functions from this repo, you would use `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` separately—this backend talks to Postgres over SQLAlchemy.

4. Apply migrations (recommended on Postgres):

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

5. Start the server:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8007
```

## WeChat / WeRead (official accounts)

These routes live under **`/api/wechat`** and use the same WeRead gateway behaviour as the `test/python` prototype (account pool, rotation on `WeReadError400`, daily block list for `429`, etc.). Most routes require a GEB JWT from **`POST /api/auth/login`**.

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/api/wechat/qr` | No — returns `{ uuid, scanUrl }` for QR login |
| `GET` | `/api/wechat/login-status?uuid=...` | Optional — if you send `Authorization: Bearer <jwt>`, a successful login attaches the WeRead session to that user |
| `GET` | `/api/wechat/accounts` | Yes |
| `POST` | `/api/wechat/accounts/clear-block` | Yes |
| `DELETE` | `/api/wechat/accounts/{vid}` | Yes |
| `POST` | `/api/wechat/mps` | Yes — body `{"wxsLink": "https://mp.weixin.qq.com/s/..."}` |
| `GET` | `/api/wechat/mps` | Yes |
| `POST` | `/api/wechat/mps/{mp_id}/sync` | Yes — add `?history=1` for full history |
| `POST` | `/api/wechat/mps/resolve-share-url` | Yes |
| `POST` | `/api/wechat/mps/by-id` | Yes |
| `POST` | `/api/wechat/mps/sync-all` | Yes |
| `DELETE` | `/api/wechat/mps/{mp_id}` | Yes |
| `GET` | `/api/wechat/articles?mpId=...` | Yes |
| `GET` | `/api/wechat/wechat-articles?mpId=...` | Yes |

Typical flow: register or log in → `GET /api/wechat/qr` → user scans → poll `login-status` **with** `Authorization: Bearer ...` so the WeRead token is stored on your user → `POST /api/wechat/mps` with an article link → `POST /api/wechat/mps/{mp_id}/sync` as needed.

## Core API endpoints

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/user/profile`
- `PUT /api/user/profile`
- `GET /api/topics`
- `POST /api/topics/follow`
- `DELETE /api/topics/unfollow`
- `GET /api/feed`
- `POST /api/articles/bookmark`
- `DELETE /api/articles/bookmark`
- `GET /api/user/bookmarks`
- `POST /api/source/mute`
- `POST /api/source/prefer`
- `POST /api/behavior/track`
- `POST /api/admin/ingest`
- `POST /api/admin/cluster`
- `POST /api/admin/rebuild`

## Worker (Celery)

WeRead feeds are refreshed on a schedule (default every 10 minutes). Override with `CELERY_WEREAD_SYNC_MINUTES` (1–59).

```bash
cd backend
source .venv/bin/activate
celery -A app.workers worker --loglevel=info
```

Beat (scheduler) in a second terminal:

```bash
celery -A app.workers beat --loglevel=info
```

Requires Redis URLs in `.env` (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`). Uses the same persistence as the API: SQLAlchemy when Supabase env vars are unset, otherwise Supabase REST.

## Tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

## Troubleshooting

- **401 on protected routes**: Send `Authorization: Bearer <access_token>` from `/api/auth/login`.
- **WeRead / gateway errors**: Try another `PLATFORM_URL`, add more WeChat accounts to your pool (`/api/wechat/qr` again after login), and keep `UPDATE_DELAY_TIME` at `60` or higher to reduce rate limiting.
- **Alembic / migration errors**: Ensure `DATABASE_URL` is set and Postgres is reachable; run `alembic current` to see revision state.

### Segmentation fault / crash when importing SQLAlchemy (`import sqlalchemy`, `pip`, or `uvicorn`)

Your crash report showed **Homebrew** Python (`/opt/homebrew/.../Python`) loading **`_pickle`** (and other stdlib C extensions) from **Anaconda** (`/opt/anaconda3/...`). Those binaries are not ABI-compatible together, which leads to `EXC_BAD_ACCESS` inside `dict_subscript` / `_pickle_init`.

**Fix (use one Python stack only):**

1. Leave all Conda envs: run `conda deactivate` until your shell prompt no longer shows `(base)` or any conda name.
2. `unset PYTHONHOME` (and avoid setting `PYTHONPATH` to Anaconda).
3. Start a **new** terminal, or put Homebrew **before** Anaconda in `PATH` (or remove Anaconda from `PATH` for this project).
4. Recreate the venv from the same interpreter you intend to run:

```bash
cd backend
rm -rf .venv
/opt/homebrew/bin/python3 -m venv .venv   # use `which python3` if not Homebrew
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
python scripts/check_python_env.py
```

If `check_python_env.py` prints `import sqlalchemy: OK`, start the API with `python -m uvicorn app.main:app --host 127.0.0.1 --port 8007`.

**Alternative:** skip Homebrew for this repo and create the venv with **only** Conda’s Python, e.g. `conda create -n geb python=3.12` and `pip install -r requirements.txt` inside that env—just do not mix Conda and Homebrew in one shell for the same venv.
