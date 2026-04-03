from fastapi import APIRouter, Depends

from ..core.deps import get_current_user
from ..schemas import UserProfileOut, UserProfileUpdate
from ..services.user_service import update_profile

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/profile", response_model=UserProfileOut)
def get_profile(current_user: dict = Depends(get_current_user)):
    return {
        "user_id": current_user["id"],
        "email": current_user["email"],
        "display_name": current_user.get("display_name"),
        "avatar_url": current_user.get("avatar_url"),
        "bio": current_user.get("bio"),
    }


@router.put("/profile", response_model=UserProfileOut)
def put_profile(payload: UserProfileUpdate, current_user: dict = Depends(get_current_user)):
    updated = update_profile(current_user["id"], payload.model_dump())
    return {
        "user_id": updated["id"],
        "email": updated["email"],
        "display_name": updated.get("display_name"),
        "avatar_url": updated.get("avatar_url"),
        "bio": updated.get("bio"),
    }
