from fastapi import APIRouter, Depends, HTTPException

from .article_access import (
    article_id_allowed_for_user_actions,
    hydrate_saved_article_rows,
)
from ..db.app_repository import AppRepository, get_repo
from ..core.deps import get_current_user
from ..schemas import BookmarkRequest, MessageResponse, ArticleOut

router = APIRouter(prefix="/api/articles", tags=["likes"])


@router.post("/like", response_model=MessageResponse)
def add_like(
    payload: BookmarkRequest,
    current_user: dict = Depends(get_current_user),
    repo: AppRepository = Depends(get_repo),
):
    uid = current_user["id"]
    if not article_id_allowed_for_user_actions(repo, uid, payload.article_id):
        raise HTTPException(status_code=404, detail="Article not found")
    repo.like_add(uid, payload.article_id)
    return {"message": "Liked"}


@router.delete("/like", response_model=MessageResponse)
def remove_like(
    payload: BookmarkRequest,
    current_user: dict = Depends(get_current_user),
    repo: AppRepository = Depends(get_repo),
):
    repo.like_remove(current_user["id"], payload.article_id)
    return {"message": "Like removed"}


user_router = APIRouter(prefix="/api/user", tags=["likes"])


@user_router.get("/likes", response_model=list[ArticleOut])
def get_likes(
    current_user: dict = Depends(get_current_user),
    repo: AppRepository = Depends(get_repo),
):
    uid = current_user["id"]
    ids = repo.like_list_article_ids(uid)
    out = hydrate_saved_article_rows(repo, uid, ids)
    out.sort(key=lambda item: item["published_at"], reverse=True)
    return out
