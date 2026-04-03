# Vercel Deployment Guide for GEB (Global Events Board)

## Architecture Overview

This app uses:
- **Frontend**: Next.js (Node.js) ✅ Fully supported by Vercel
- **Backend**: FastAPI (Python) ⚠️ Limited support via Serverless Functions
- **Database**: SQLite (local) ❌ NOT suitable for Vercel
- **Job Queue**: Celery + Redis ⚠️ Requires external service

## Problem & Solution

### ❌ Current Issues with Direct Vercel Deployment

1. **SQLite won't persist** - Vercel's filesystem resets on each deployment
2. **Celery/Redis won't work** - No persistent background job support
3. **Execution time limits** - Python functions limited to 120s max

### ✅ Recommended Solution: Hybrid Deployment

Deploy **frontend to Vercel** and **backend separately**:

| Component | Platform | Reason |
|-----------|----------|--------|
| Frontend (Next.js) | **Vercel** | Perfect match, zero config needed |
| Backend (FastAPI) | **Railway/Render** | Better for Python, persistent runtime, databases |
| Database | **Vercel Postgres or Railway Postgres** | Persistent, managed |
| Redis/Job Queue | **Upstash Redis** | Serverless, auto-scaling |

## Step 1: Deploy Frontend to Vercel Only

```bash
# 1. Push to GitHub
git add .
git commit -m "chore: prepare for Vercel deployment"
git push

# 2. Go to https://vercel.com
# 3. Click "Add New..." → "Project"
# 4. Import from Git (select this repo)
# 5. Framework Preset: Next.js (auto-detected)
# 6. Click Deploy
```

**Environment Variables (Frontend)**:
```
NEXT_PUBLIC_API_URL=https://your-backend-url.com
```

---

## Step 2a: Deploy Backend to Railway (RECOMMENDED)

Railway is the best choice for Python FastAPI and PostgreSQL:

### Quick Start:

1. **Sign up**: https://railway.app
2. **Create new project** → "Deploy from GitHub"
3. **Select this repo**
4. **Add PostgreSQL plugin**:
   - Railway automatically creates `DATABASE_URL`
   - Railway automatically creates `REDIS_URL` (via Redis plugin)
5. **Configure environment variables** (see below)
6. **Deploy**

### Backend Environment Variables for Railway:

```bash
# .env (for local testing)
DATABASE_URL=postgresql://user:password@localhost/geb_db
CELERY_BROKER_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120
```

### Backend Environment Variables for Railway Dashboard:

```
DATABASE_URL        → Auto-set by Railway Postgres plugin
REDIS_URL           → Auto-set by Railway Redis plugin  
CELERY_BROKER_URL   → ${{REDIS_URL}}
SECRET_KEY          → generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
ALGORITHM           → HS256
ACCESS_TOKEN_EXPIRE_MINUTES → 120
```

---

## Step 2b: Alternative - Deploy Backend to Render

If you prefer Render:

1. Go to https://render.com
2. Create new Web Service
3. Connect GitHub repository
4. Configure:
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add PostgreSQL database
6. Add Redis database

---

## Step 3: Update Frontend to Use Remote Backend

Edit `frontend/services/` files to use the deployed backend URL:

```typescript
// frontend/services/api.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
});
```

Update `next.config.js` (if needed):

```javascript
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
};

module.exports = nextConfig;
```

---

## Step 4: Database Migration

### Convert SQLite to PostgreSQL

Your current code needs one change in `backend/app/db/database.py`:

```python
# BEFORE (SQLite - won't work on Vercel):
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{db_dir}/geb.db")

# AFTER (PostgreSQL - works everywhere):
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/geb_db")
```

Run migrations:
```bash
cd backend
python -c "from app.db import Base, engine; Base.metadata.create_all(bind=engine)"
```

---

## Step 5: Update CORS Settings

Edit `backend/app/main.py`:

```python
# BEFORE (only localhost):
allow_origins=[
    "http://127.0.0.1:3000",
    "http://localhost:3000",
],

# AFTER (allow Vercel frontend):
allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://your-frontend.vercel.app",
    os.getenv("FRONTEND_URL", "http://localhost:3000"),
],
```

---

## Full Deployment Checklist

- [ ] Frontend code pushed to GitHub
- [ ] Backend code pushed to GitHub
- [ ] Create Railway/Render account
- [ ] Deploy frontend to Vercel
- [ ] Deploy backend to Railway/Render
- [ ] Create PostgreSQL database
- [ ] Create Redis instance (Upstash or Railway)
- [ ] Set environment variables in all services
- [ ] Update CORS in backend
- [ ] Update API URLs in frontend
- [ ] Test API connectivity
- [ ] Monitor logs and fix issues

---

## Debugging Tips

### Frontend won't connect to backend?
```bash
# Check CORS headers
curl -i -X OPTIONS https://your-backend-url.com/api/auth/login

# Check environment variable
vercel env list
vercel env pull  # pulls env from Vercel
```

### Backend crashing on Railway?
```bash
# Check logs
railway logs

# Restart service
railway service restart
```

### Database connection failing?
```bash
# Test connection locally
psql $DATABASE_URL

# Check if migrations ran
# Look at backend logs for startup errors
```

---

## Cost Estimation (Monthly)

| Service | Free Tier | Paid |
|---------|-----------|------|
| **Vercel Frontend** | ✅ Included | $99/mo |
| **Railway** | $5 credits | $0/mo + usage |
| **Upstash Redis** | Free 10,000 ops | $0.20 per 1M ops |
| **PostgreSQL** | Railway $5 | Railway included |

**Minimum cost: $0-5/mo** (with free tiers)

---

## Next Steps

1. Run `vercel init` (optional, auto-detects monorepo)
2. Deploy frontend: `git push` → push to GitHub → Vercel auto-deploys
3. Deploy backend to Railway following the setup guide
4. Update environment variables in Vercel and Railway dashboards
5. Test full integration
