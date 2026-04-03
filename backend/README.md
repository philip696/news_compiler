# Backend MVP (FastAPI)

## Run

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8007
```

Open docs: `http://127.0.0.1:8007/docs`

## Core endpoints

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

## Worker scaffold

```bash
cd backend
source .venv/bin/activate
celery -A workers.celery_app.celery_app worker --loglevel=info
```

## Tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```
