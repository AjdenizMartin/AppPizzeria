from fastapi import APIRouter
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.database import models
from app.schemas.user import UserCreate, UserLogin
from app.main import hash_password, verify_password, SECRET_KEY, ALGORITHM
from jose import jwt
from datetime import datetime, timedelta

router = APIRouter()


@router.post("/register")
def register(user: UserCreate):
    db: Session = SessionLocal()

    new_user = models.User(
        email=user.email,
        password=hash_password(user.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created"}


@router.post("/login")
def login(user: UserLogin):
    db: Session = SessionLocal()

    db_user = db.query(models.User).filter(
        models.User.email == user.email
    ).first()

    if not db_user:
        return {"error": "User not found"}

    if not verify_password(user.password, db_user.password):
        return {"error": "Wrong password"}

    token = jwt.encode(
        {
            "sub": db_user.email,
            "exp": datetime.utcnow() + timedelta(hours=2)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return {"access_token": token}