from fastapi import APIRouter, Depends, HTTPException

from ..db.app_repository import AppRepository, get_repo
from ..core.security import create_access_token
from ..schemas import RegisterRequest, LoginRequest, TokenResponse, UserOut
from ..services.auth_service import register_user, login_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
def register(payload: RegisterRequest, repo: AppRepository = Depends(get_repo)):
    try:
        user = register_user(payload.username, payload.password, repo)
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, repo: AppRepository = Depends(get_repo)):
    user = login_user(payload.username, payload.password, repo)
    token = create_access_token(
        {
            "user_id": user["id"],
            "username": user["username"],
            "role": "user",
        }
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: LoginRequest, repo: AppRepository = Depends(get_repo)):
    user = login_user(payload.username, payload.password, repo)
    token = create_access_token(
        {
            "user_id": user["id"],
            "username": user["username"],
            "role": "user",
        }
    )
    return {"access_token": token, "token_type": "bearer"}

