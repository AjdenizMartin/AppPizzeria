from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db, require_owner
from app.core.limiter import limiter
from app.database.models import User
from app.schemas.user import (
    TokenResponse,
    UserLogin,
    UserProfileUpdate,
    UserRead,
    UserRegister,
    UserRoleUpdate,
)
from app.services.auth_service import (
    authenticate_user,
    build_token_response,
    list_users,
    register_user,
    update_user_profile,
    update_user_role,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: UserRegister, db: Session = Depends(get_db)):
    try:
        user = register_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return build_token_response(user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return build_token_response(user)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me/profile", response_model=UserRead)
def update_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_user_profile(db, current_user, payload)


@router.get("/admin/users", response_model=list[UserRead])
def get_users(
    db: Session = Depends(get_db),
    _owner: User = Depends(require_owner),
):
    return list_users(db)


@router.patch("/admin/users/{user_id}/role", response_model=UserRead)
def patch_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    _owner: User = Depends(require_owner),
):
    updated = update_user_role(db, user_id, payload.role)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return updated
