from fastapi import APIRouter, Depends

from ..core.deps import get_current_user
from ..schemas import BehaviorRequest, MessageResponse
from ..services.user_service import record_behavior

router = APIRouter(prefix="/api/behavior", tags=["behavior"])


@router.post("/track", response_model=MessageResponse)
def track_behavior(payload: BehaviorRequest, current_user: dict = Depends(get_current_user)):
    record_behavior(current_user["id"], payload.model_dump())
    return {"message": "Behavior tracked"}
