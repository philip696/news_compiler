from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import state
from ..db.database import get_db
from ..db.models import Bookmark
from ..core.deps import get_current_user
from ..schemas import BookmarkRequest, MessageResponse, ArticleOut

router = APIRouter(prefix="/api/articles", tags=["bookmarks"])


@router.post("/bookmark", response_model=MessageResponse)
def add_bookmark(payload: BookmarkRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.article_id not in state.articles:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Check if bookmark already exists
    existing = db.query(Bookmark).filter(
        Bookmark.user_id == current_user["id"],
        Bookmark.article_id == payload.article_id
    ).first()
    
    if not existing:
        bookmark = Bookmark(user_id=current_user["id"], article_id=payload.article_id)
        db.add(bookmark)
        db.commit()
    
    return {"message": "Bookmarked"}


@router.delete("/bookmark", response_model=MessageResponse)
def remove_bookmark(payload: BookmarkRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    bookmark = db.query(Bookmark).filter(
        Bookmark.user_id == current_user["id"],
        Bookmark.article_id == payload.article_id
    ).first()
    
    if bookmark:
        db.delete(bookmark)
        db.commit()
    
    return {"message": "Bookmark removed"}


@router.get("/user/bookmarks", response_model=list[ArticleOut], include_in_schema=False)
def _legacy_bookmark_route(current_user: dict = Depends(get_current_user)):
    return []


user_router = APIRouter(prefix="/api/user", tags=["bookmarks"])


@user_router.get("/bookmarks", response_model=list[ArticleOut])
def get_bookmarks(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    bookmarks = db.query(Bookmark).filter(Bookmark.user_id == current_user["id"]).all()
    out = []
    for bookmark in bookmarks:
        article = state.articles.get(bookmark.article_id)
        if not article:
            continue
        out.append(article)
    out.sort(key=lambda item: item["published_at"], reverse=True)
    return out
