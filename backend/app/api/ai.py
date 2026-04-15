from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
import logging

from ..core.deps import get_current_user
from ..services.ai_service import get_ai_service
from .. import state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


class SummarizeRequest(BaseModel):
    article_id: str = Field(..., description="Article ID to summarize")
    max_length: int = Field(200, ge=50, le=500, description="Max summary length")


class SentimentRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Text to analyze")


class TagsRequest(BaseModel):
    article_id: str = Field(..., description="Article ID to generate tags for")
    count: int = Field(5, ge=1, le=10, description="Number of tags to generate")


class QuestionRequest(BaseModel):
    article_id: str = Field(..., description="Article ID to question about")
    question: str = Field(..., min_length=5, description="Question about the article")


@router.get("/health")
async def ai_health(current_user: dict = Depends(get_current_user)):
    """Check if AI service is available."""
    ai_service = get_ai_service()
    is_healthy = await ai_service.health_check()
    
    if not is_healthy:
        raise HTTPException(
            status_code=503,
            detail="AI service (Ollama) is not available. Make sure it's running at http://localhost:11434"
        )
    
    return {"status": "healthy", "service": "ollama"}


@router.post("/summarize")
async def summarize_article(
    request: SummarizeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Summarize an article using AI."""
    # Find article in state
    if request.article_id not in state.articles:
        raise HTTPException(status_code=404, detail="Article not found")
    
    article = state.articles[request.article_id]
    
    try:
        ai_service = get_ai_service()
        
        # Extract content (handle different article formats)
        title = article.get("title", "Untitled")
        content = article.get("content") or article.get("description") or ""
        
        if not content:
            raise HTTPException(status_code=400, detail="Article has no content to summarize")
        
        summary = await ai_service.summarize_article(
            title=title,
            content=content,
            max_length=request.max_length,
        )
        
        return {
            "article_id": request.article_id,
            "title": title,
            "summary": summary,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summarization error: {e}")
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")


@router.post("/sentiment")
async def analyze_sentiment(
    request: SentimentRequest,
    current_user: dict = Depends(get_current_user),
):
    """Analyze sentiment of text."""
    try:
        ai_service = get_ai_service()
        result = await ai_service.analyze_sentiment(request.text)
        
        return {
            "text": request.text[:100] + "..." if len(request.text) > 100 else request.text,
            "sentiment": result.get("sentiment"),
            "confidence": result.get("confidence"),
            "reason": result.get("reason"),
        }
    
    except Exception as e:
        logger.error(f"Sentiment analysis error: {e}")
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")


@router.post("/tags")
async def generate_tags(
    request: TagsRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generate tags for an article."""
    # Find article
    if request.article_id not in state.articles:
        raise HTTPException(status_code=404, detail="Article not found")
    
    article = state.articles[request.article_id]
    
    try:
        ai_service = get_ai_service()
        
        title = article.get("title", "Untitled")
        content = article.get("content") or article.get("description") or ""
        
        if not content:
            raise HTTPException(status_code=400, detail="Article has no content")
        
        tags = await ai_service.generate_tags(
            title=title,
            content=content,
            count=request.count,
        )
        
        return {
            "article_id": request.article_id,
            "title": title,
            "tags": tags,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tag generation error: {e}")
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")


@router.post("/ask")
async def ask_article(
    request: QuestionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Ask a question about an article."""
    # Find article
    if request.article_id not in state.articles:
        raise HTTPException(status_code=404, detail="Article not found")
    
    article = state.articles[request.article_id]
    
    try:
        ai_service = get_ai_service()
        
        title = article.get("title", "Untitled")
        content = article.get("content") or article.get("description") or ""
        
        if not content:
            raise HTTPException(status_code=400, detail="Article has no content")
        
        answer = await ai_service.answer_question(
            question=request.question,
            article_title=title,
            article_content=content,
        )
        
        return {
            "article_id": request.article_id,
            "title": title,
            "question": request.question,
            "answer": answer,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Question answering error: {e}")
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")
