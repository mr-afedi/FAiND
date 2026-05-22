"""
FastAPI dependency injection helpers — JWT guards, DB session, etc.
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_access_token
from app.models.user import User, AccountStatus, UserRole
from app.services.auth_service import get_user_by_id

bearer_scheme = HTTPBearer(auto_error=False)


def _get_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_current_user(
    payload: dict = Depends(_get_token_payload),
    db: Session = Depends(get_db),
) -> User:
    user_id = payload.get("sub")
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if user.status == AccountStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended.",
        )
    if user.status != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active.",
        )
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Returns the authenticated user if a valid token is present, or None for guests.
    Use for endpoints that are public but behave differently when authenticated.
    """
    if not credentials:
        return None
    payload = verify_access_token(credentials.credentials)
    if not payload:
        return None
    user_id = payload.get("sub")
    user = get_user_by_id(db, user_id)
    if not user or user.status != AccountStatus.ACTIVE:
        return None
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (
        UserRole.ASSISTANT_ROOT_ADMIN,
        UserRole.ROOT_ADMIN,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


def require_root_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ROOT_ADMIN:
        # Return 404 — don't reveal that this route exists
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return current_user
