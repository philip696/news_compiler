from fastapi import APIRouter, Depends, Query, HTTPException
import random

from ..core.deps import get_current_user
from ..db.app_repository import AppRepository, get_repo
from ..recommendation.ranker import rank_feed_for_user
from ..schemas import FeedResponse, ArticleOut, ArticleDetailOut
from .. import state

router = APIRouter(prefix="/api/feed", tags=["feed"])

def _fallback_story_feed(limit: int) -> list[dict]:
    """Build a basic feed when clustering/ranking data is temporarily unavailable."""
    if not state.articles:
        return []
    recent_articles = sorted(
        state.articles.values(),
        key=lambda article: article.get("published_at"),
        reverse=True,
    )[:limit]
    stories = []
    for article in recent_articles:
        stories.append(
            {
                "cluster_id": f"fallback_{article['id']}",
                "topic": article.get("topic", "general"),
                "headline": article.get("title", "Untitled"),
                "summary": article.get("content", "")[:160],
                "article_count": 1,
                "sources": [article.get("source_name", "unknown")],
                "score": 0.0,
                "articles": [article],
            }
        )
    return stories


@router.get("", response_model=FeedResponse)
def get_feed(
    current_user: dict = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
):
    """Get personalized feed with pagination support."""
    all_stories = rank_feed_for_user(current_user["id"])
    if not all_stories:
        # Ranking can be empty if clustering has not finished yet; return
        # a recency-based feed so the home page is never blank.
        all_stories = _fallback_story_feed(limit=max(limit + skip, 50))
    
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
async def get_category_articles(
    category_name: str,
    current_user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=500),
):
    """Get articles from a specific category."""
    if category_name not in state.available_categories and category_name not in state.explore_categories:
        raise HTTPException(status_code=404, detail=f"Category '{category_name}' not found")
    
    category_articles = state.articles_by_category.get(category_name, [])

    if not category_articles:
        raise HTTPException(status_code=404, detail=f"No articles found for category '{category_name}'")

    # WebHose articles first, Kaggle articles last
    webhose = [a for a in category_articles if a["id"].startswith("webhose_")]
    kaggle  = [a for a in category_articles if not a["id"].startswith("webhose_")]

    web_sel    = webhose[:min(limit, len(webhose))]
    remain     = limit - len(web_sel)
    kaggle_sel = random.sample(kaggle, min(remain, len(kaggle))) if remain > 0 else []
    selected   = web_sel + kaggle_sel

    return {
        "category": category_name,
        "articles": selected,
        "total": len(selected),
    }


@router.get("/article/{article_id}", response_model=ArticleDetailOut)
def get_article(
    article_id: str,
    current_user: dict = Depends(get_current_user),
    repo: AppRepository = Depends(get_repo),
):
    """Get full article details by ID with like/bookmark (main feed or WeRead / WeChat)."""
    uid = current_user["id"]
    if article_id in state.articles:
        article = state.articles[article_id].copy()
    else:
        weread = repo.weread_articles_as_feed_dicts(uid, frozenset([article_id]))
        row = weread.get(article_id)
        if not row:
            raise HTTPException(status_code=404, detail="Article not found")
        article = row.copy()

    article["liked"] = repo.like_exists(uid, article_id)
    article["bookmarked"] = repo.bookmark_exists(uid, article_id)
    return article


def _article_to_cluster(article: dict) -> dict:
    """Wrap a flat article dict in a StoryClusterOut-compatible structure."""
    published_at = article.get("published_at")
    if hasattr(published_at, "isoformat"):
        published_at = published_at.isoformat()
    return {
        "cluster_id": article["id"],
        "topic": article.get("topic", "general"),
        "headline": article.get("title", ""),
        "summary": article.get("content", "")[:300],
        "article_count": 1,
        "sources": [article.get("source_name", "")],
        "score": float(article.get("topic_confidence", 0.5)),
        "articles": [
            {
                "id": article["id"],
                "title": article.get("title", ""),
                "content": article.get("content", ""),
                "url": article.get("url", ""),
                "source_id": article.get("source_id", ""),
                "source_name": article.get("source_name", ""),
                "published_at": published_at,
                "topic": article.get("topic", "general"),
                "topic_confidence": float(article.get("topic_confidence", 0.5)),
                "logo_url": article.get("logo_url", ""),
                "main_image": article.get("main_image", ""),
            }
        ],
    }


@router.get("/explore", response_model=FeedResponse)
def get_explore_feed(
    current_user: dict = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get explore feed with articles from Kaggle dataset."""
    all_articles = list(state.articles_explore.values())

    random.shuffle(all_articles)

    page = all_articles[skip : skip + limit]
    stories = [_article_to_cluster(a) for a in page]

    return {
        "stories": stories,
        "total": len(all_articles),
        "skip": skip,
        "limit": limit,
    }


@router.get("/search", response_model=FeedResponse)
def search_articles(
    q: str = Query(..., min_length=1),
    limit: int = Query(40, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    """Full-text search across all articles (title + content)."""
    q_lower = q.strip().lower()
    # WebHose articles first (id starts with "webhose_"), then Kaggle (UUID)
    webhose = [a for a in state.articles.values() if a["id"].startswith("webhose_")]
    kaggle = [a for a in state.articles.values() if not a["id"].startswith("webhose_")]

    def matches(a: dict) -> bool:
        return q_lower in a.get("title", "").lower() or q_lower in a.get("content", "").lower()

    results = [a for a in webhose if matches(a)] + [a for a in kaggle if matches(a)]
    results = results[:limit]
    stories = [_article_to_cluster(a) for a in results]
    return {"stories": stories, "total": len(stories), "skip": 0, "limit": limit}


@router.get("/explore/categories")
def get_explore_categories(current_user: dict = Depends(get_current_user)):
    """Get list of available explore categories."""
    # Include both explore categories (Kaggle) and available categories (WeChat, News)
    categories = list(set(state.explore_categories + state.available_categories))
    return {"categories": sorted(categories)}


@router.get("/explore/category/{category_name}", response_model=FeedResponse)
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

    selected = random.sample(category_articles, min(limit, len(category_articles)))
    stories = [_article_to_cluster(a) for a in selected]

    return {
        "stories": stories,
        "total": len(stories),
        "skip": 0,
        "limit": limit,
    }
