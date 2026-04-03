"""Chatbot API endpoints for article summarization and advanced search."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from ..core.deps import get_current_user
from ..services.chatbot_service import chatbot
from pydantic import BaseModel

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])

class SummarizeRequest(BaseModel):
    """Request model for article summarization."""
    article_id: str
    article_content: str
    article_title: str

class SearchRequest(BaseModel):
    """Request model for advanced article search."""
    query: str
    topic: Optional[str] = None
    keywords: Optional[List[str]] = None
    limit: int = 5

@router.post("/summarize")
def summarize_article(
    request: SummarizeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Summarize an article using DeepSeek AI.
    
    Args:
        request: Contains article_id, article_content, article_title
        current_user: Authenticated user
    
    Returns:
        Dictionary with article_id, original_content, and summary
    """
    try:
        summary = chatbot.summarize_article(request.article_content, request.article_title)
        
        return {
            'article_id': request.article_id,
            'title': request.article_title,
            'summary': summary,
            'status': 'success'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")

@router.post("/search")
def search_and_compile(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """Search and compile articles based on query and filters.
    
    Args:
        request: Contains query, optional topic, keywords, and limit
        current_user: Authenticated user
    
    Returns:
        Dictionary with query, synthesis, matching articles, and metadata
    """
    try:
        result = chatbot.search_and_compile(
            query=request.query,
            topic=request.topic,
            keywords=request.keywords,
            limit=request.limit
        )
        
        return {
            'query': result['query'],
            'filters': result['filters'],
            'synthesis': result['synthesis'],
            'articles': result['articles'],
            'total': result['count'],
            'status': 'success'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/quick-search")
def quick_search(
    q: str = Query(..., description="Search query"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    limit: int = Query(5, ge=1, le=20, description="Number of results"),
    current_user: dict = Depends(get_current_user)
):
    """Quick search endpoint for simple queries.
    
    Args:
        q: Search query string
        topic: Optional topic filter
        limit: Number of results to return
        current_user: Authenticated user
    
    Returns:
        List of matching articles with scores
    """
    try:
        articles = chatbot.search_articles(q, topic=topic, top_k=limit)
        
        return {
            'query': q,
            'articles': articles,
            'count': len(articles),
            'status': 'success'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quick search failed: {str(e)}")

@router.get("/health")
def chatbot_health():
    """Check chatbot service health and API key status."""
    import os
    
    has_api_key = bool(os.getenv("DEEPSEEK_API_KEY"))
    has_articles = len(chatbot.articles) > 0
    
    return {
        'status': 'healthy' if (has_api_key and has_articles) else 'degraded',
        'deepseek_api_configured': has_api_key,
        'articles_indexed': len(chatbot.articles),
        'vectorizer_ready': chatbot.article_vectors is not None
    }
