# Personalized News Aggregation MVP

This workspace contains a runnable MVP for personalized news aggregation and discovery.

## Project structure

- `backend/` FastAPI API, ingestion pipeline, clustering, ranking, worker scaffold
- `frontend/` Next.js UI for feed, topics, source preferences, and bookmarks

## Backend quickstart

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8007
```

Backend docs: `http://127.0.0.1:8007/docs`

## Frontend quickstart

```bash
cd frontend
npm install
npm run dev
```

Frontend app: `http://127.0.0.1:3000`

## MVP coverage

- JWT auth (`/api/auth/register`, `/api/auth/login`, `/api/auth/refresh`)
- Personalized feed (`/api/feed`)
- Topics follow/unfollow (`/api/topics/*`)
- Source preferences (`/api/source/mute`, `/api/source/prefer`)
- Bookmarks (`/api/articles/bookmark`, `/api/user/bookmarks`)
- Adaptive learning from behavior (`/api/behavior/track`)
- Ingestion + clustering admin triggers (`/api/admin/ingest`, `/api/admin/cluster`, `/api/admin/rebuild`)
- Celery worker scaffold with 5-min ingestion and 10-min clustering schedules
