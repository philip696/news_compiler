from fastapi import APIRouter, Depends, HTTPException

from .article_access import (
    article_id_allowed_for_user_actions,
    hydrate_saved_article_rows,
)
from ..db.app_repository import AppRepository, get_repo
from ..core.deps import get_current_user
from ..schemas import BookmarkRequest, MessageResponse, ArticleOut

router = APIRouter(prefix="/api/articles", tags=["bookmarks"])


@router.post("/bookmark", response_model=MessageResponse)
def add_bookmark(
    payload: BookmarkRequest,
    current_user: dict = Depends(get_current_user),
    repo: AppRepository = Depends(get_repo),
):
    uid = current_user["id"]
    if not article_id_allowed_for_user_actions(repo, uid, payload.article_id):
        raise HTTPException(status_code=404, detail="Article not found")
    repo.bookmark_add(uid, payload.article_id)
    return {"message": "Bookmarked"}


@router.delete("/bookmark", response_model=MessageResponse)
def remove_bookmark(
    payload: BookmarkRequest,
    current_user: dict = Depends(get_current_user),
    repo: AppRepository = Depends(get_repo),
):
    repo.bookmark_remove(current_user["id"], payload.article_id)
    return {"message": "Bookmark removed"}


@router.get("/user/bookmarks", response_model=list[ArticleOut], include_in_schema=False)
def _legacy_bookmark_route(current_user: dict = Depends(get_current_user)):
    return []


user_router = APIRouter(prefix="/api/user", tags=["bookmarks"])


@user_router.get("/bookmarks", response_model=list[ArticleOut])
def get_bookmarks(
    current_user: dict = Depends(get_current_user),
    repo: AppRepository = Depends(get_repo),
):
    uid = current_user["id"]
    ids = repo.bookmark_list_article_ids(uid)
    out = hydrate_saved_article_rows(repo, uid, ids)
    out.sort(key=lambda item: item["published_at"], reverse=True)
    return out
