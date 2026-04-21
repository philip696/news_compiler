import httpx
import json
import logging
from typing import Optional

from ..core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-powered tasks using DeepSeek's OpenAI-compatible chat API."""

    def __init__(self):
        self.base_url = settings.DEEPSEEK_BASE_URL or "https://api.deepseek.com"
        self.api_key = settings.DEEPSEEK_API_KEY
        self.model = settings.DEEPSEEK_MODEL or "deepseek-chat"
        self.timeout = 120

        if not self.api_key:
            logger.warning(
                "DEEPSEEK_API_KEY is not set; AIService is disabled. "
                "AI-powered endpoints will return 503 until the key is configured."
            )

    def _require_key(self) -> None:
        if not self.api_key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY is not configured. Set it in the deployment environment."
            )

    async def health_check(self) -> bool:
        """Check if DeepSeek API is reachable and the key works."""
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"DeepSeek health check failed: {e}")
            return False

    async def summarize_article(
        self,
        title: str,
        content: str,
        max_length: int = 200,
    ) -> str:
        if not content:
            raise ValueError("Article content cannot be empty")

        content_truncated = content[:3000]
        user_prompt = (
            f"Summarize the following article in {max_length} words or less. "
            f"Be concise and capture the main points.\n\n"
            f"Title: {title}\n\nContent:\n{content_truncated}"
        )
        return await self._chat(
            system="You are a concise news summarization assistant.",
            user=user_prompt,
            temperature=0.3,
        )

    async def analyze_sentiment(self, text: str) -> dict:
        user_prompt = (
            "Analyze the sentiment of the following text and respond with ONLY valid JSON:\n"
            '{"sentiment": "positive|negative|neutral", "confidence": 0.0-1.0, "reason": "brief explanation"}\n\n'
            f"Text: {text}"
        )
        response = await self._chat(
            system="You are a sentiment classifier. Respond with JSON only.",
            user=user_prompt,
            temperature=0.0,
        )
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
        except Exception as e:
            logger.error(f"Sentiment parse error: {e}")
        return {"sentiment": "unknown", "confidence": 0.0, "reason": "Could not parse response"}

    async def generate_tags(self, title: str, content: str, count: int = 5) -> list[str]:
        content_truncated = content[:2000]
        user_prompt = (
            f"Generate {count} relevant tags for this article. "
            "Return ONLY a comma-separated list of tags, no other text.\n\n"
            f"Title: {title}\n\nContent:\n{content_truncated}"
        )
        response = await self._chat(
            system="You generate short, relevant tags.",
            user=user_prompt,
            temperature=0.3,
        )
        tags = [tag.strip() for tag in response.split(",") if tag.strip()]
        return tags[:count]

    async def answer_question(self, question: str, article_title: str, article_content: str) -> str:
        content_truncated = article_content[:3000]
        user_prompt = (
            f"Article Title: {article_title}\n\n"
            f"Article Content:\n{content_truncated}\n\n"
            f"Question: {question}\n\nAnswer concisely based only on the article."
        )
        return await self._chat(
            system="You answer questions strictly grounded in the supplied article.",
            user=user_prompt,
            temperature=0.2,
        )

    async def _chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        """Call DeepSeek /chat/completions (OpenAI-compatible) with a system+user message."""
        self._require_key()
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "temperature": temperature,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                if resp.status_code != 200:
                    raise Exception(f"DeepSeek API error: {resp.status_code} - {resp.text}")
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        except httpx.ConnectError:
            logger.error(f"Cannot connect to DeepSeek at {self.base_url}")
            raise Exception(
                "AI service unavailable. Check DEEPSEEK_API_KEY and network access to api.deepseek.com."
            )
        except Exception as e:
            logger.error(f"DeepSeek API call failed: {e}")
            raise


_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
