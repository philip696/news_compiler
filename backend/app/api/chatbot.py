"""Chatbot API endpoints for article summarization, search, and conversational AI."""

import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from ..core.deps import get_current_user
from ..services.chatbot_service import chatbot
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str   # "user" | "assistant" | "system"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context: Optional[str] = None   # page-level context injected by the frontend

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
async def summarize_article(
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
        summary = await chatbot.summarize_article(request.article_content, request.article_title)
        
        return {
            'article_id': request.article_id,
            'title': request.article_title,
            'summary': summary,
            'status': 'success'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")

@router.post("/search")
async def search_and_compile(
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
        result = await chatbot.search_and_compile(
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

@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Conversational chat powered by DeepSeek."""
    api_key = os.getenv("DEEPSEEK_API_KEY", "")

    if not api_key:
        raise HTTPException(status_code=503, detail="DeepSeek API key not configured")

    base_system = (
        "You are Synergy AI, an intelligent news assistant built into the Synergy "
        "news platform. You help users understand articles, discover trends, and "
        "answer questions about current events. Be concise, insightful, and friendly. "
        "When the user asks you to summarize or discuss an article, use the article "
        "content provided in the context section below — never say you cannot access it."
    )
    if request.context:
        base_system += f"\n\n--- Current page context ---\n{request.context}\n--- End context ---"

    system_msg = {"role": "system", "content": base_system}

    payload = {
        "model": "deepseek-chat",
        "messages": [system_msg] + [m.dict() for m in request.messages],
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.deepseek.com/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            reply = data["choices"][0]["message"]["content"]
            return {"reply": reply}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"DeepSeek API error: {e.response.text}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="DeepSeek timed out — please try again.")
    except httpx.ConnectError as e:
        raise HTTPException(status_code=502, detail=f"Cannot reach DeepSeek: {repr(e)}")
    except (KeyError, IndexError, ValueError) as e:
        raise HTTPException(status_code=502, detail=f"Unexpected DeepSeek response format: {repr(e)}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"DeepSeek request failed: {type(e).__name__}: {repr(e)}")


@router.get("/health")
def chatbot_health():
    """Check chatbot service health and DeepSeek API status."""
    try:
        from ..core.config import settings
        import asyncio

        has_key = bool(settings.DEEPSEEK_API_KEY)
        has_url = bool(settings.DEEPSEEK_BASE_URL)
        has_articles = len(chatbot.articles) > 0

        try:
            health = asyncio.run(chatbot.ai_service.health_check())
        except Exception:
            health = False

        return {
            'status': 'healthy' if (has_key and has_articles and health) else 'degraded',
            'deepseek_configured': has_key and has_url,
            'deepseek_accessible': health,
            'articles_indexed': len(chatbot.articles),
            'vectorizer_ready': chatbot.article_vectors is not None,
            'ai_model': settings.DEEPSEEK_MODEL or 'deepseek-chat',
            'ai_endpoint': settings.DEEPSEEK_BASE_URL or 'https://api.deepseek.com',
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
            'deepseek_configured': False,
        }
