from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
import httpx

from . import state
from .core.config import settings
from .db import Base, engine
from .db.supabase_client import use_supabase_runtime
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
from .api.wechat import router as wechat_router
from .services.weread_service import WeReadService, DEFAULT_PLATFORM_URL

# Create tables for SQLAlchemy/SQLite local runs only (Supabase: use SQL editor or Alembic).
if not use_supabase_runtime():
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup ingestion + WeRead HTTP client for the app's lifetime."""
    import asyncio

    from .startup import run_startup_sequence

    async def _ingest_in_background():
        """WebHose + Kaggle load can take minutes on small hosts; must not block listen."""
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, run_startup_sequence)
        except Exception as e:
            print(f"⚠️  Startup sequence error (app continues): {e}", flush=True)

    # ── WeRead HTTP client ─────────────────────────────────────────────────
    timeout = httpx.Timeout(15.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        app.state.weread_http = client
        app.state.weread_service = WeReadService(
            client=client,
            platform_url=os.getenv("PLATFORM_URL", DEFAULT_PLATFORM_URL),
        )
        ingest_sync = os.getenv("STARTUP_INGEST_SYNC", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if ingest_sync:
            await _ingest_in_background()
        else:
            asyncio.create_task(_ingest_in_background())
            print(
                "📥 Startup ingestion running in background (/healthz is ready). "
                "Set STARTUP_INGEST_SYNC=1 to block until ingest finishes.",
                flush=True,
            )
        try:
            yield
        finally:
            app.state.weread_service = None
            app.state.weread_http = None


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

# Build list of allowed origins dynamically
allowed_origins = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:3001",
    "http://localhost:3001",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:8080",  # Alternative frontend ports
    "http://localhost:8080",
    "https://newscompiler-production.vercel.app",  # Production Vercel
]

# Add any env-configured URL
if frontend_url := os.getenv("FRONTEND_URL"):
    allowed_origins.append(frontend_url)
if vercel_url := os.getenv("VERCEL_URL"):
    allowed_origins.append(f"https://{vercel_url}")

# Configure CORS middleware - MUST be first middleware added
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Explicitly allow these origins
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",  # Allow any localhost port
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
    max_age=3600,
)

app.add_middleware(GZipMiddleware, minimum_size=800)

# Mount static files for serving images and data
data_path = Path(__file__).parent.parent / "data"
if data_path.exists():
    app.mount("/data", StaticFiles(directory=str(data_path)), name="data")




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
app.include_router(wechat_router)


@app.on_event("shutdown")
def shutdown_event():
    """Graceful shutdown."""
    print("\n" + "="*60)
    print("🛑 SHUTDOWN SIGNAL RECEIVED")
    print("="*60)
    print(f"Final state: {len(state.articles)} articles, {len(state.clusters)} clusters")
    print("="*60 + "\n")


# Global exception handler for better error visibility
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with logging."""
    print(f"⚠️  HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    print(f"❌ Unexpected error: {type(exc).__name__}: {exc}")
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
