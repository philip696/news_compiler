from fastapi import APIRouter, Depends, HTTPException

from .. import state
from ..core.deps import get_current_user
from ..schemas import SourcePreferenceRequest, MessageResponse

router = APIRouter(prefix="/api/source", tags=["sources"])


def _set_preference(current_user: dict, source_id: str, value: str):
    if source_id not in state.SOURCES:
        raise HTTPException(status_code=404, detail="Source not found")
    state.ensure_user_state(current_user["id"])
    state.user_source_preferences[current_user["id"]][source_id] = value


@router.post("/mute", response_model=MessageResponse)
def mute_source(payload: SourcePreferenceRequest, current_user: dict = Depends(get_current_user)):
    _set_preference(current_user, payload.source_id, "muted")
    return {"message": "Source muted"}


@router.post("/prefer", response_model=MessageResponse)
def prefer_source(payload: SourcePreferenceRequest, current_user: dict = Depends(get_current_user)):
    _set_preference(current_user, payload.source_id, "preferred")
    return {"message": "Source preferred"}


@router.post("/neutral", response_model=MessageResponse)
def neutral_source(payload: SourcePreferenceRequest, current_user: dict = Depends(get_current_user)):
    _set_preference(current_user, payload.source_id, "neutral")
    return {"message": "Source set neutral"}
