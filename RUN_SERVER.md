# GEB Application - Server Startup

## Prerequisites
- Python 3.13+  
- Virtual environment activated at `.venv/`
- Dependencies installed from `backend/requirements.txt`

## Start Backend Server

```bash
cd backend
PYTHONPATH=/Users/philipdewanto/Downloads/Code/GEB/backend \
../. venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Start Frontend Development Server

```bash
cd frontend
npm run dev
```

## Verify Integration

1. Backend API: http://localhost:8000
2. Frontend: http://localhost:3000
3. API Docs: http://localhost:8000/docs

## Yahoo Finance Integration

- 8 finance articles load during startup
- Available at: `GET /api/feed?category=Finance`
- Fallback strategy with exponential backoff (3 retries)
- Displays in feed with source "Motley Fool / Yahoo Finance" etc

## Test Suite

Run all tests:
```bash
./..venv/bin/python -m pytest backend/test_yahoo_finance_integration.py -v
```

All 5 integration tests passing.
