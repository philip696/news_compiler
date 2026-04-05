from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
import re

from . import state
from .core.config import settings
from .db import Base, engine
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
# Allow localhost in dev and all Vercel deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app.*",  # Match any Vercel domain (prod & preview)
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
    """Startup tasks with comprehensive error handling and diagnostics."""
    from .startup import run_startup_sequence
    try:
        run_startup_sequence()
    except Exception as e:
        print(f"⚠️  STARTUP HANDLER ERROR (app will continue): {e}")
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
