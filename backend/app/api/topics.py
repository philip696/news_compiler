from fastapi import APIRouter, Depends, HTTPException

from .. import state
from ..core.deps import get_current_user
from ..schemas import TopicOut, FollowTopicRequest, MessageResponse

router = APIRouter(prefix="/api/topics", tags=["topics"])


@router.get("", response_model=list[TopicOut])
def get_topics(current_user: dict = Depends(get_current_user)):
    state.ensure_user_state(current_user["id"])
    records = state.user_topics[current_user["id"]]
    return [
        {
            "id": topic,
            "name": topic,
            "followed": records[topic]["followed"],
            "interest_score": records[topic]["interest_score"],
        }
        for topic in state.TOPICS
    ]


@router.post("/follow", response_model=MessageResponse)
def follow_topic(payload: FollowTopicRequest, current_user: dict = Depends(get_current_user)):
    if payload.topic_id not in state.TOPICS:
        raise HTTPException(status_code=404, detail="Topic not found")

    state.ensure_user_state(current_user["id"])
    rec = state.user_topics[current_user["id"]][payload.topic_id]
    rec["followed"] = True
    rec["interest_score"] = max(0.6, rec["interest_score"])
    rec["updated_at"] = state.now_utc()
    return {"message": "Topic followed"}


@router.delete("/unfollow", response_model=MessageResponse)
def unfollow_topic(payload: FollowTopicRequest, current_user: dict = Depends(get_current_user)):
    if payload.topic_id not in state.TOPICS:
        raise HTTPException(status_code=404, detail="Topic not found")

    state.ensure_user_state(current_user["id"])
    rec = state.user_topics[current_user["id"]][payload.topic_id]
    rec["followed"] = False
    rec["interest_score"] = max(0.1, rec["interest_score"] * 0.7)
    rec["updated_at"] = state.now_utc()
    return {"message": "Topic unfollowed"}
