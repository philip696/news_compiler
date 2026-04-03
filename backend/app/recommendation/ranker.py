import math
from datetime import timezone, datetime

from .. import state
from ..core.config import settings


def _source_pref_weight(value: str | None) -> float:
    if value == "preferred":
        return 1.0
    if value == "muted":
        return -1.0
    return 0.0


def _recency_score(published_at: datetime) -> float:
    now = datetime.now(timezone.utc)
    hours = max(0.01, (now - published_at).total_seconds() / 3600)
    return math.exp(-hours / 24)


def _user_behavior_score(user_id: str, topic: str) -> float:
    events = state.reading_history.get(user_id, [])
    topic_events = [event for event in events if event.get("topic") == topic]
    if not topic_events:
        return 0.0
    clicks = sum(1 for e in topic_events if e.get("clicked"))
    bookmarks = sum(1 for e in topic_events if e.get("bookmarked"))
    return min(1.0, (clicks * 0.08) + (bookmarks * 0.12) + (len(topic_events) * 0.02))


def rank_feed_for_user(user_id: str) -> list[dict]:
    state.ensure_user_state(user_id)
    topic_map = state.user_topics[user_id]
    source_prefs = state.user_source_preferences.get(user_id, {})

    scored = []
    for cluster in state.clusters.values():
        article_ids = cluster["article_ids"]
        if not article_ids:
            continue

        cluster_articles = [state.articles[aid] for aid in article_ids if aid in state.articles]
        if not cluster_articles:
            continue

        if all(source_prefs.get(a["source_id"]) == "muted" for a in cluster_articles):
            continue

        topic_match = min(1.0, max(0.0, topic_map[cluster["topic"]]["interest_score"]))

        source_preference = sum(
            _source_pref_weight(source_prefs.get(article["source_id"])) for article in cluster_articles
        ) / max(1, len(cluster_articles))

        popularity_raw = sum(state.article_popularity.get(article["id"], 0) for article in cluster_articles)
        popularity = min(1.0, popularity_raw / 50)
        recency = max(_recency_score(article["published_at"]) for article in cluster_articles)
        user_behavior = _user_behavior_score(user_id, cluster["topic"])

        score = (
            (topic_match * 0.40)
            + (source_preference * 0.20)
            + (popularity * 0.15)
            + (recency * 0.15)
            + (user_behavior * 0.10)
        )

        scored.append((score, cluster, cluster_articles))

    scored.sort(key=lambda item: item[0], reverse=True)

    output = []
    for score, cluster, cluster_articles in scored[: settings.top_n_stories]:
        output.append(
            {
                "cluster_id": cluster["cluster_id"],
                "topic": cluster["topic"],
                "headline": cluster["headline"],
                "summary": cluster["summary"],
                "article_count": len(cluster_articles),
                "sources": cluster["sources"],
                "score": round(score, 6),
                "articles": cluster_articles,
            }
        )
    return output
