# 📋 Deployment Quick Reference

## URLs After Deployment

| Component | URL |
|-----------|-----|
| **Frontend** | https://your-app.vercel.app |
| **Backend API** | https://your-backend-xxx.up.railway.app |
| **API Docs** | https://your-backend-xxx.up.railway.app/docs (Swagger UI) |
| **GitHub Repo** | [Your repo on GitHub](https://github.com) |

---

## Critical Environment Variables

### Vercel (Frontend Dashboard)

```
NEXT_PUBLIC_API_URL = https://your-backend-xxx.up.railway.app
```

### Railway (Backend Dashboard)

```
DATABASE_URL                    → Auto-set ✅
REDIS_URL                       → Auto-set ✅
CELERY_BROKER_URL              = ${{REDIS_URL}}
CELERY_RESULT_BACKEND          = ${{REDIS_URL}}
SECRET_KEY                     = [Generate new]
ALGORITHM                      = HS256
ACCESS_TOKEN_EXPIRE_MINUTES    = 120
FRONTEND_URL                   = https://your-app.vercel.app
```

---

## Quick Redeploy Process

When you make changes:

```bash
# 1. Commit and push
git add .
git commit -m "feat: your change"
git push origin main

# 2. Vercel auto-redeploys (check at vercel.com)
# 3. Railway auto-redeploys (check at railway.app)
# 4. Done! No manual steps needed
```

---

## Useful Commands

### Test Backend Locally
```bash
cd backend
uvicorn app.main:app --reload
```

### Test Frontend Locally
```bash
cd frontend
npm run dev
```

### Connect Frontend to Local Backend
```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Run Migrations on Production
```bash
# Via Railway CLI:
railway shell --service backend
python -c "from app.db import Base, engine; Base.metadata.create_all(bind=engine)"
```

---

## Support Links

- **Vercel Docs**: https://vercel.com/docs
- **Railway Docs**: https://docs.railway.app
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Next.js Docs**: https://nextjs.org/docs

---

## Emergency Fixes

### Backend not responding?
1. Railway Dashboard → Backend Service → "Logs"
2. Check for errors
3. Click "Redeploy" button
4. Wait 2-3 minutes

### Frontend shows blank page?
1. Vercel Dashboard → "Deployments" → "Redeploy"
2. Check browser console (F12) for errors
3. Verify `NEXT_PUBLIC_API_URL` is correct

### Database connection failed?
1. Railway Dashboard → PostgreSQL Service
2. Check status (should be green)
3. Click "Restart" if needed
4. Restart Backend service after

---

## Performance Tips

- [ ] Enable Vercel Analytics
- [ ] Monitor Railway disk usage
- [ ] Check API response times in Swagger UI
- [ ] Use Railway metrics tab
- [ ] Set up log retention alerts

---

## Security Checklist

- [ ] `SECRET_KEY` is random and strong (32+ chars)
- [ ] Never commit `.env` file to Git
- [ ] Rotate `SECRET_KEY` monthly
- [ ] Enable Railway GitHub integration for auto-deploys
- [ ] Use HTTPS only (both platforms default to this)
- [ ] Keep dependencies updated

---

Generated: 2026-04-03
Last Updated: [Update this as you change configs]
