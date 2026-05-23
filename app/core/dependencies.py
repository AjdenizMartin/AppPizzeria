from collections.abc import Generator

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import PRINT_AGENT_KEY
from app.core.security import decode_access_token
from app.database.database import SessionLocal
from app.database.models import User
from app.services.auth_service import get_user_by_id

bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    user = get_user_by_id(db, int(user_id))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found for token",
        )

    return user


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    user = get_user_by_id(db, int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found for token",
        )

    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    role = (current_user.role or "").lower()
    if current_user.is_admin and role not in {"owner", "manager", "staff"}:
        current_user.role = "owner"
    if not current_user.is_admin and role not in {"owner", "manager", "staff"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user


def require_owner(current_user: User = Depends(get_current_user)) -> User:
    role = (current_user.role or "").lower()
    if role == "owner" or (current_user.is_admin and role == ""):
        return current_user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner access required")


def require_manager_or_owner(current_user: User = Depends(get_current_user)) -> User:
    role = (current_user.role or "").lower()
    if role in {"owner", "manager"} or (current_user.is_admin and role == ""):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Manager or owner access required",
    )


def require_staff_or_manager_or_owner(current_user: User = Depends(get_current_user)) -> User:
    role = (current_user.role or "").lower()
    if role in {"owner", "manager", "staff"} or (current_user.is_admin and role == ""):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Staff, manager or owner access required",
    )


def require_print_agent(
    x_print_agent_key: str | None = Header(default=None, alias="X-Print-Agent-Key"),
) -> None:
    if not PRINT_AGENT_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PRINT_AGENT_KEY is not configured on the server",
        )

    if x_print_agent_key != PRINT_AGENT_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid print agent credentials",
        )
