# 🚀 Step-by-Step Vercel Deployment Guide

## Quick Summary

This app has:
- **Frontend**: Next.js (React) - ✅ Deploy to Vercel
- **Backend**: FastAPI (Python) - ✅ Deploy to Railway.app
- **Database**: PostgreSQL - ✅ Railway handles this
- **Cache/Jobs**: Redis - ✅ Upstash or Railway

**Total Setup Time**: ~15 minutes

---

## Phase 1: Prepare Your Code (5 minutes)

### 1.1 Push to GitHub

```bash
# From project root
git add .
git commit -m "chore: prepare for Vercel + Railway deployment"
git push origin main
```

### 1.2 Create Environment Variable Files

Create `backend/.env.local` for local testing:

```bash
cd backend
cp .env.production .env
```

---

## Phase 2: Deploy Frontend to Vercel (3 minutes)

### 2.1 Create Vercel Account

1. Go to https://vercel.com
2. Click "Sign Up"
3. Choose "GitHub" and authorize

### 2.2 Deploy Frontend

1. Click "+ Add New..." → "Project"
2. Select your GitHub repository
3. **Framework Preset**: Next.js (auto-detected)
4. **Root Directory**: `./frontend`
5. **Environment Variables**: 
   - Key: `NEXT_PUBLIC_API_URL`
   - Value: (leave empty for now, we'll set it after backend deploys)
6. Click "Deploy"

**Result**: Your app is now at `https://your-app.vercel.app`

### 2.3 Get Your Vercel Frontend URL

After deployment, copy the URL from Vercel dashboard (e.g., `https://geb.vercel.app`)

---

## Phase 3: Deploy Backend to Railway (7 minutes)

### 3.1 Create Railway Account

1. Go to https://railway.app
2. Sign up with GitHub
3. Authorize Railway to access your repo

### 3.2 Create Backend Project on Railway

1. Click "New Project" → "+ New" → "GitHub Repo"
2. Select your repository
3. Click "Deploy Now"

Railway auto-detects the Dockerfile and deploys

### 3.3 Add PostgreSQL Database

1. In Railway project, click "+ Add"
2. Select "Database" → "PostgreSQL"
3. Railway **automatically creates** `DATABASE_URL` environment variable

### 3.4 Add Redis (for Celery)

1. Click "+ Add" again
2. Select "Database" → "Redis"
3. Copy the Redis URL, use as both:
   - `CELERY_BROKER_URL`
   - `CELERY_RESULT_BACKEND`

### 3.5 Configure Environment Variables in Railway

In Railway dashboard, go to Backend service → "Variables":

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Auto-set by PostgreSQL plugin ✅ |
| `REDIS_URL` | Auto-set by Redis plugin ✅ |
| `CELERY_BROKER_URL` | `${{REDIS_URL}}` |
| `CELERY_RESULT_BACKEND` | `${{REDIS_URL}}` |
| `SECRET_KEY` | Generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `120` |
| `FRONTEND_URL` | Your Vercel frontend URL (e.g., `https://geb.vercel.app`) |

### 3.6 Deploy Backend

1. Push any changes: `git push`
2. Railway automatically redeploys
3. Watch deployment in Railway dashboard
4. Once green, click the service to get the public URL

**Result**: Your backend is now at `https://your-backend-xxx.up.railway.app`

---

## Phase 4: Connect Frontend to Backend (2 minutes)

### 4.1 Update Vercel Environment Variables

1. Go to Vercel Dashboard
2. Select your project
3. Go to "Settings" → "Environment Variables"
4. Update `NEXT_PUBLIC_API_URL`:
   - Value: `https://your-backend-xxx.up.railway.app`
5. Click "Save"
6. Trigger a redeploy: Go to "Deployments" → click the latest → "Redeploy"

### 4.2 Update Railway Backend CORS

In Railway, update Backend service variables:

| Key | Value |
|-----|-------|
| `FRONTEND_URL` | `https://your-app.vercel.app` |

Redeploy backend.

---

## Phase 5: Test the Integration (3 minutes)

### 5.1 Test Backend Health

```bash
curl https://your-backend-xxx.up.railway.app/docs
# Should show Swagger UI
```

### 5.2 Test Frontend

1. Open `https://your-app.vercel.app` in browser
2. Open DevTools → "Network" tab
3. Try to log in or fetch data
4. Check that requests go to your Railway backend ✅

### 5.3 Verify Database

```bash
# From Railway CLI or dashboard
railway shell --service backend
# Then run:
python -c "from app.db import SessionLocal; print('DB connected!')"
```

---

## Troubleshooting Guide

### ❌ Frontend shows CORS error

```
Access to XMLHttpRequest blocked by CORS policy
```

**Fix**:
1. Check Railway backend `FRONTEND_URL` is set correctly
2. Restart the backend service
3. Check backend logs: Railway Dashboard → Backend → "Logs"

### ❌ "Cannot connect to backend"

**Check**:
```bash
# Test if backend is running
curl -v https://your-backend-xxx.up.railway.app

# Should return 200 status code
```

If 503 or timeout:
1. Check Railway logs for errors
2. Check if PostgreSQL is connected: `DATABASE_URL` env var exists
3. Restart backend service

### ❌ Database errors in Railway logs

```
ERROR: psycopg2.OperationalError: could not translate host name
```

**Fix**:
1. Restart PostgreSQL service first
2. Then restart Backend service
3. Wait 30 seconds for connection to stabilize

### ❌ "SECRET_KEY not set"

**Fix**:
1. Generate in Railway dashboard variables
2. Or run locally: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
3. Copy to Railway variables
4. Redeploy

---

## Post-Deployment Checklist

- [ ] Frontend deployed to Vercel (https://...)
- [ ] Backend deployed to Railway (https://...)
- [ ] PostgreSQL database connected (Railway shows green)
- [ ] Redis connected (Railway shows green)
- [ ] `FRONTEND_URL` set in Railway backend
- [ ] `NEXT_PUBLIC_API_URL` set in Vercel frontend
- [ ] Frontend can call backend API (no CORS errors)
- [ ] Can log in and fetch data
- [ ] Profile page loads user data from database
- [ ] Bookmarks/likes persist in database

---

## Monitoring & Maintenance

### Weekly Check:
```bash
# Test API endpoint
curl https://your-backend-xxx.up.railway.app/api/feed

# Should return article feed
```

### Monthly Tasks:
1. Check Railway disk usage (data folder)
2. Monitor Vercel build minutes
3. Review logs for errors
4. Test payment flow if applicable

### Auto-Redeploy on Push:
- Vercel: ✅ Automatic on git push
- Railway: ✅ Automatic on git push

---

## Cost Summary (Monthly)

| Service | Free Tier | Paid |
|---------|-----------|------|
| **Vercel** | 100 GB bandwidth | $20+/mo |
| **Railway** | $5/mo credits | $0 with credits/month |
| **Upstash Redis** | Free 10K ops | $0.20-1/mo |
| **Total** | **$5/mo** | **$5-30/mo** |

---

## Advanced: Custom Domain (Optional)

### Add Custom Domain to Vercel
1. Vercel Dashboard → "Settings" → "Domains"
2. Add your domain
3. Update DNS records (Vercel provides instructions)

### Add Custom Domain to Railway
1. Railway Dashboard → Backend Service → "Settings"
2. Add custom domain
3. Update DNS records

---

## Next Steps

After deployment:
1. ✅ Share the frontend URL with users
2. ✅ Set up GitHub Actions for CI/CD (optional)
3. ✅ Add monitoring alerts
4. ✅ Set up automated backups
5. ✅ Document API endpoints for your team

Enjoy your deployed app! 🎉
