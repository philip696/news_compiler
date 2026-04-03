from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
import random

from ..core.deps import get_current_user
from ..db.database import get_db
from ..db.models import Bookmark, Like
from ..recommendation.ranker import rank_feed_for_user
from ..schemas import FeedResponse, ArticleOut, ArticleDetailOut
from .. import state

router = APIRouter(prefix="/api/feed", tags=["feed"])


@router.get("", response_model=FeedResponse)
def get_feed(
    current_user: dict = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
):
    """Get personalized feed with pagination support."""
    all_stories = rank_feed_for_user(current_user["id"])
    
    # Paginate results
    paginated_stories = all_stories[skip : skip + limit]
    
    return {
        "stories": paginated_stories,
        "total": len(all_stories),
        "skip": skip,
        "limit": limit,
    }


@router.get("/categories")
def get_categories(current_user: dict = Depends(get_current_user)):
    """Get list of available categories."""
    return {"categories": state.available_categories}


@router.get("/category/{category_name}", response_model=dict)
def get_category_articles(
    category_name: str,
    current_user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=500),
):
    """Get articles from a specific category. Loads 50 random articles from that category."""
    if category_name not in state.available_categories:
        raise HTTPException(status_code=404, detail=f"Category '{category_name}' not found")
    
    # Get articles from this category
    category_articles = state.articles_by_category.get(category_name, [])
    
    if not category_articles:
        raise HTTPException(status_code=404, detail=f"No articles found for category '{category_name}'")
    
    # Select random articles up to limit
    selected = random.sample(category_articles, min(limit, len(category_articles)))
    
    # Load them into the main articles dict temporarily
    for article in selected:
        state.articles[article["id"]] = article
    
    return {
        "category": category_name,
        "articles": selected,
        "total": len(selected),
    }


@router.get("/article/{article_id}", response_model=ArticleDetailOut)
def get_article(
    article_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full article details by ID with like/bookmark status."""
    if article_id not in state.articles:
        raise HTTPException(status_code=404, detail="Article not found")
    
    article = state.articles[article_id].copy()
    
    # Check if user has liked this article
    liked = db.query(Like).filter(
        Like.user_id == current_user["id"],
        Like.article_id == article_id
    ).first() is not None
    
    # Check if user has bookmarked this article
    bookmarked = db.query(Bookmark).filter(
        Bookmark.user_id == current_user["id"],
        Bookmark.article_id == article_id
    ).first() is not None
    
    article["liked"] = liked
    article["bookmarked"] = bookmarked
    
    return article


@router.get("/explore", response_model=FeedResponse)
def get_explore_feed(
    current_user: dict = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get explore feed with articles from Kaggle dataset."""
    all_articles = list(state.articles_explore.values())
    
    # Simple shuffle for variety
    random.shuffle(all_articles)
    
    paginated_stories = all_articles[skip : skip + limit]
    
    return {
        "stories": paginated_stories,
        "total": len(all_articles),
        "skip": skip,
        "limit": limit,
    }


@router.get("/explore/categories")
def get_explore_categories(current_user: dict = Depends(get_current_user)):
    """Get list of available explore categories."""
    return {"categories": state.explore_categories}


@router.get("/explore/category/{category_name}", response_model=dict)
def get_explore_category_articles(
    category_name: str,
    current_user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=500),
):
    """Get articles from a specific explore category."""
    if category_name not in state.explore_categories:
        raise HTTPException(status_code=404, detail=f"Category '{category_name}' not found in explore feed")
    
    category_articles = state.articles_explore_by_category.get(category_name, [])
    
    if not category_articles:
        raise HTTPException(status_code=404, detail=f"No articles found for category '{category_name}'")
    
    # Select random articles up to limit
    selected = random.sample(category_articles, min(limit, len(category_articles)))
    
    # Load them into the explore articles dict temporarily
    for article in selected:
        state.articles_explore[article["id"]] = article
    
    return {
        "category": category_name,
        "articles": selected,
        "total": len(selected),
    }
