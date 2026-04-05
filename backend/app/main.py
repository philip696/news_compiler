from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os

from . import state
from .core.config import settings
from .db import Base, engine
from .ingestion.loader import ingest_webhose_jsonl, ingest_mock_feed, ingest_kaggle_dataset
from .clustering.engine import build_story_clusters
from .api.auth import router as auth_router
from .api.user import router as user_router
from .api.topics import router as topics_router
from .api.feed import router as feed_router
from .api.bookmarks import router as bookmarks_router, user_router as bookmarks_user_router
from .api.likes import router as likes_router, user_router as likes_user_router
from .api.sources import router as sources_router
from .api.behavior import router as behavior_router
from .api.admin import router as admin_router
from .api.chatbot import router as chatbot_router

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, version="0.1.0")

# Configure CORS for both local development and production
# Allow localhost in dev, Vercel frontend in production
allowed_origins = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

# Add frontend URL from environment if specified
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    allowed_origins.append(frontend_url)

# Add Vercel preview deployments
vercel_url = os.getenv("VERCEL_URL")
if vercel_url:
    allowed_origins.append(f"https://{vercel_url}")
    allowed_origins.append(f"http://{vercel_url}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving images and data
data_path = Path(__file__).parent.parent / "data"
if data_path.exists():
    app.mount("/data", StaticFiles(directory=str(data_path)), name="data")


@app.on_event("startup")
def startup_event():
    """Startup tasks: ingest data synchronously, defer clustering to background."""
    from . import state
    
    # Skip if already ingested (prevent re-ingestion on container restart)
    if state.startup_complete:
        print("✅ Startup already completed, skipping data ingestion")
        return
    
    try:
        ingest_mock_feed()
    except Exception as e:
        print(f"⚠️  Mock feed ingestion failed: {e}")
    
    try:
        ingest_kaggle_dataset()
    except Exception as e:
        print(f"⚠️  Kaggle dataset ingestion failed: {e}")
    
    # Mark startup as complete BEFORE clustering
    state.startup_complete = True
    print("✅ Data ingestion complete, deferring clustering to background")
    
    # Defer expensive clustering to background task
    try:
        import threading
        import traceback
        
        def cluster_in_background():
            try:
                print("🔄 Starting background clustering...")
                build_story_clusters()
                print(f"✅ Clustering complete: {len(state.clusters)} clusters")
            except Exception as e:
                print(f"❌ CRITICAL: Background clustering failed!")
                print(f"Error: {e}")
                traceback.print_exc()
                print("App will continue running without clusters")
        
        cluster_thread = threading.Thread(target=cluster_in_background, daemon=True)
        cluster_thread.start()
    except Exception as e:
        print(f"⚠️  Background clustering setup failed: {e}")
        import traceback
        traceback.print_exc()


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "articles": len(state.articles),
        "clusters": len(state.clusters),
    }


app.include_router(auth_router)
app.include_router(user_router)
app.include_router(topics_router)
app.include_router(feed_router)
app.include_router(bookmarks_router)
app.include_router(bookmarks_user_router)
app.include_router(likes_router)
app.include_router(likes_user_router)
app.include_router(sources_router)
app.include_router(behavior_router)
app.include_router(admin_router)
app.include_router(chatbot_router)
