from fastapi import HTTPException
from .. import state
from ..core.config import settings


def get_user(user_id: str) -> dict:
    user = state.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def update_profile(user_id: str, payload: dict) -> dict:
    user = get_user(user_id)
    for key in ["display_name", "avatar_url", "bio"]:
        if key in payload and payload[key] is not None:
            user[key] = payload[key]
    return user


def record_behavior(user_id: str, event: dict):
    state.ensure_user_state(user_id)
    article = state.articles.get(event["article_id"])
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    topic = article["topic"]
    topic_record = state.user_topics[user_id][topic]

    for topic_key in state.user_topics[user_id]:
        state.user_topics[user_id][topic_key]["interest_score"] *= settings.decay_factor

    delta = event["reading_time"] * settings.learning_rate / 60.0
    if event.get("clicked"):
        delta += 0.08
    if event.get("bookmarked"):
        delta += 0.12
    if event.get("skipped"):
        delta -= 0.06

    topic_record["interest_score"] = max(0.0, min(1.5, topic_record["interest_score"] + delta))
    topic_record["updated_at"] = state.now_utc()

    event_record = {**event, "topic": topic, "timestamp": state.now_utc().isoformat()}
    state.reading_history[user_id].append(event_record)

    state.article_popularity[event["article_id"]] = state.article_popularity.get(event["article_id"], 0) + 1
