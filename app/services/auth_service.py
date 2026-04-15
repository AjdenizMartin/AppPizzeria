from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import ADMIN_EMAILS
from app.core.security import create_access_token, hash_password, verify_password
from app.database.models import User
from app.schemas.user import TokenResponse, UserLogin, UserProfileUpdate, UserRead, UserRegister


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized_email = normalize_email(email)
    return db.scalar(select(User).where(User.email == normalized_email))


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def _first_user_should_be_admin(db: Session) -> bool:
    user_count = db.scalar(select(func.count()).select_from(User)) or 0
    return user_count == 0


def register_user(db: Session, payload: UserRegister) -> User:
    email = normalize_email(payload.email)

    if get_user_by_email(db, email) is not None:
        raise ValueError("A user with that email already exists")

    is_admin = email in ADMIN_EMAILS or _first_user_should_be_admin(db)

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        is_admin=is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(db: Session, payload: UserLogin) -> User | None:
    user = get_user_by_email(db, payload.email)

    if user is None:
        return None

    if not verify_password(payload.password, user.hashed_password):
        return None

    return user


def build_token_response(user: User) -> TokenResponse:
    access_token = create_access_token(
        subject=str(user.id),
        email=user.email,
        is_admin=user.is_admin,
    )
    return TokenResponse(
        access_token=access_token,
        user=UserRead.model_validate(user),
    )


def update_user_profile(db: Session, user: User, payload: UserProfileUpdate) -> User:
    user.full_name = payload.full_name.strip() or None
    user.address_line = payload.address_line.strip() or None
    user.city = payload.city.strip() or None
    user.postal_code = payload.postal_code.strip() or None
    user.phone = payload.phone.strip() or None
    db.commit()
    db.refresh(user)
    return user
