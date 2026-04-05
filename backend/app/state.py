from datetime import datetime, timezone
from typing import Any


TOPICS = ["technology", "politics", "finance", "sports", "science", "health"]

SOURCES = {
    "reuters": {
        "id": "reuters",
        "name": "Reuters",
        "domain": "reuters.com",
        "logo_url": "/images/logos/reuters.png"
    },
    "bbc": {
        "id": "bbc",
        "name": "BBC",
        "domain": "bbc.com",
        "logo_url": "/images/logos/bbc.png"
    },
    "cnn": {
        "id": "cnn",
        "name": "CNN",
        "domain": "cnn.com",
        "logo_url": "/images/logos/cnn.png"
    },
    "techcrunch": {
        "id": "techcrunch",
        "name": "TechCrunch",
        "domain": "techcrunch.com",
        "logo_url": "/images/logos/techcrunch.png"
    },
    "theverge": {
        "id": "theverge",
        "name": "The Verge",
        "domain": "theverge.com",
        "logo_url": "/images/logos/theverge.jpg"
    },
}

# Startup control
startup_complete: bool = False
now_utc = lambda: datetime.now(timezone.utc)

users: dict[str, dict[str, Any]] = {}
users_by_email: dict[str, str] = {}
user_topics: dict[str, dict[str, dict[str, Any]]] = {}
user_source_preferences: dict[str, dict[str, str]] = {}
bookmarks: dict[str, set[str]] = {}
likes: dict[str, set[str]] = {}
reading_history: dict[str, list[dict[str, Any]]] = {}

articles: dict[str, dict[str, Any]] = {}
clusters: dict[str, dict[str, Any]] = {}
article_popularity: dict[str, int] = {}
available_categories: list[str] = []
articles_by_category: dict[str, list[dict[str, Any]]] = {}
available_categories: list[str] = []
articles_by_category: dict[str, list[dict[str, Any]]] = {}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ensure_user_state(user_id: str):
    if user_id not in user_topics:
        user_topics[user_id] = {
            topic: {
                "topic_id": topic,
                "followed": False,
                "interest_score": 0.2,
                "updated_at": now_utc(),
            }
            for topic in TOPICS
        }
    if user_id not in user_source_preferences:
        user_source_preferences[user_id] = {}
    if user_id not in bookmarks:
        bookmarks[user_id] = set()
    if user_id not in likes:
        likes[user_id] = set()
    if user_id not in reading_history:
        reading_history[user_id] = []

# Explore feed (Kaggle dataset)
articles_explore: dict[str, dict[str, Any]] = {}
explore_categories: list[str] = []
articles_explore_by_category: dict[str, list[dict[str, Any]]] = {}
article_explore_popularity: dict[str, int] = {}
