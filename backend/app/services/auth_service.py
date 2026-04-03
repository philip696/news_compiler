from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..db.models import User
from ..core import security


def register_user(username: str, password: str, db: Session) -> dict:
    # Check if username already exists
    existing_username = db.query(User).filter(User.username == username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create new user
    hashed_password = security.hash_password(password)
    user = User(username=username, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"id": user.id, "username": user.username}


def login_user(username: str, password: str, db: Session) -> dict:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not security.verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {"id": user.id, "username": user.username}

