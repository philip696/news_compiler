from fastapi import HTTPException

from ..core import security
from ..db.app_repository import AppRepository


def register_user(username: str, password: str, repo: AppRepository) -> dict:
    if repo.user_get_by_username(username):
        raise HTTPException(status_code=400, detail="Username already taken")
    hashed_password = security.hash_password(password)
    return repo.user_create(username, hashed_password)


def login_user(username: str, password: str, repo: AppRepository) -> dict:
    user = repo.user_get_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not security.verify_password(password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"id": user["id"], "username": user["username"]}
