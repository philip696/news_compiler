import httpx
import logging
from typing import Optional
from ..core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-powered tasks like summaries, analysis, etc."""
    
    def __init__(self):
        # Ollama Cloud API endpoint
        self.ollama_url = settings.OLLAMA_BASE_URL or "https://api.ollama.com"
        self.api_key = settings.OLLAMA_API_KEY
        self.model = settings.OLLAMA_MODEL or "mistral"  # mistral is faster and good for summaries
        self.timeout = 120  # AI requests can take time
        
        if not self.api_key:
            logger.warning(
                "OLLAMA_API_KEY is not set; AIService is disabled. "
                "AI-powered endpoints will return 503 until the key is configured."
            )

    def _require_key(self) -> None:
        if not self.api_key:
            raise RuntimeError(
                "OLLAMA_API_KEY is not configured. Set it in the deployment environment."
            )
    
    async def health_check(self) -> bool:
        """Check if Ollama Cloud API is available."""
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = await client.get(f"{self.ollama_url}/api/tags", headers=headers)
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama Cloud API health check failed: {e}")
            return False
    
    async def summarize_article(
        self,
        title: str,
        content: str,
        max_length: int = 200,
    ) -> str:
        """Summarize an article using local AI."""
        if not content:
            raise ValueError("Article content cannot be empty")
        
        # Truncate content if too long to avoid timeout
        max_tokens = 3000
        content_truncated = content[:max_tokens]
        
        prompt = f"""Summarize the following article in {max_length} words or less. Be concise and capture the main points.

Title: {title}

Content:
{content_truncated}

Summary:"""
        
        try:
            return await self._call_ai(prompt)
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            raise
    
    async def analyze_sentiment(self, text: str) -> dict:
        """Analyze sentiment of text (positive, negative, neutral)."""
        prompt = f"""Analyze the sentiment of the following text and respond with ONLY valid JSON in this format:
{{"sentiment": "positive|negative|neutral", "confidence": 0.0-1.0, "reason": "brief explanation"}}

Text: {text}

Response (JSON only):"""
        
        try:
            response = await self._call_ai(prompt)
            # Try to extract JSON from response
            import json
            # Find JSON object in response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
            return {"sentiment": "unknown", "confidence": 0.0, "reason": "Could not parse response"}
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            raise
    
    async def generate_tags(self, title: str, content: str, count: int = 5) -> list[str]:
        """Generate tags for an article."""
        content_truncated = content[:2000]
        
        prompt = f"""Generate {count} relevant tags for this article. Return only the tags as a comma-separated list, no other text.

Title: {title}

Content:
{content_truncated}

Tags:"""
        
        try:
            response = await self._call_ai(prompt)
            # Parse comma-separated tags
            tags = [tag.strip() for tag in response.split(',')]
            return tags[:count]
        except Exception as e:
            logger.error(f"Tag generation error: {e}")
            raise
    
    async def answer_question(self, question: str, article_title: str, article_content: str) -> str:
        """Answer a question about an article."""
        content_truncated = article_content[:3000]
        
        prompt = f"""Based on the following article, answer this question concisely:

Article Title: {article_title}

Article Content:
{content_truncated}

Question: {question}

Answer:"""
        
        try:
            return await self._call_ai(prompt)
        except Exception as e:
            logger.error(f"Question answering error: {e}")
            raise
    
    async def _call_ai(self, prompt: str) -> str:
        """Call Ollama Cloud API with the prompt."""
        self._require_key()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "temperature": 0.3,  # Lower temperature for more consistent results
                    },
                    headers=headers
                )
                
                if response.status_code != 200:
                    raise Exception(f"Ollama Cloud API error: {response.status_code} - {response.text}")
                
                data = response.json()
                return data.get("response", "").strip()
        
        except httpx.ConnectError:
            logger.error(f"Cannot connect to Ollama Cloud API at {self.ollama_url}")
            raise Exception(
                f"AI service unavailable. Check your OLLAMA_API_KEY and ensure the API endpoint is accessible."
            )
        except Exception as e:
            logger.error(f"AI API call failed: {e}")
            raise


# Singleton instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get or create AI service instance."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
