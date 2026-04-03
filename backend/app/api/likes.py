from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import state
from ..db.database import get_db
from ..db.models import Like
from ..core.deps import get_current_user
from ..schemas import BookmarkRequest, MessageResponse, ArticleOut

router = APIRouter(prefix="/api/articles", tags=["likes"])


@router.post("/like", response_model=MessageResponse)
def add_like(payload: BookmarkRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.article_id not in state.articles:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Check if like already exists
    existing = db.query(Like).filter(
        Like.user_id == current_user["id"],
        Like.article_id == payload.article_id
    ).first()
    
    if not existing:
        like = Like(user_id=current_user["id"], article_id=payload.article_id)
        db.add(like)
        db.commit()
    
    return {"message": "Liked"}


@router.delete("/like", response_model=MessageResponse)
def remove_like(payload: BookmarkRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    like = db.query(Like).filter(
        Like.user_id == current_user["id"],
        Like.article_id == payload.article_id
    ).first()
    
    if like:
        db.delete(like)
        db.commit()
    
    return {"message": "Like removed"}


user_router = APIRouter(prefix="/api/user", tags=["likes"])


@user_router.get("/likes", response_model=list[ArticleOut])
def get_likes(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    likes = db.query(Like).filter(Like.user_id == current_user["id"]).all()
    out = []
    for like in likes:
        article = state.articles.get(like.article_id)
        if not article:
            continue
        out.append(article)
    out.sort(key=lambda item: item["published_at"], reverse=True)
    return out
