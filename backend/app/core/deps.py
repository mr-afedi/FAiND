"""
FastAPI dependency injection helpers — JWT guards, DB session, etc.
"""
import uuid

from fastapi import Depends, HTTPException, status, Header
from app.core.config import get_settings
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_access_token
from app.models.user import User, AccountStatus, UserRole
from app.models.authority import Authority
from app.services.auth_service import get_user_by_id
from app.services.authority_service import get_authority_by_id
from app.services.supervisor_service import get_supervisor_by_id

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
    if current_user.role != UserRole.ROOT_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


def require_root_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ROOT_ADMIN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return current_user


def _admin_secret_ok(secret_path: str | None) -> bool:
    settings = get_settings()
    configured = (settings.ADMIN_SECRET_PATH or "").strip()
    if not configured:
        return False
    return (secret_path or "").strip() == configured


def require_admin_secret(
    x_admin_secret_path: str | None = Header(None, alias="X-Admin-Secret-Path"),
) -> None:
    """Secret admin route guard — returns 404 when path does not match (Section 26.1)."""
    if not _admin_secret_ok(x_admin_secret_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")


def require_admin_access(
    _: None = Depends(require_admin_secret),
    current_user: User = Depends(require_admin),
) -> User:
    return current_user


def require_root_admin_access(
    _: None = Depends(require_admin_secret),
    current_user: User = Depends(require_root_admin),
) -> User:
    return current_user


def require_redemption_admin(current_user: User = Depends(get_current_user)) -> User:
    """Root Admin only — supervisors use /supervisor/redemption/lookup."""
    if current_user.role != UserRole.ROOT_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Redemption admin access required.",
        )
    return current_user


def require_redemption_admin_access(
    _: None = Depends(require_admin_secret),
    current_user: User = Depends(require_redemption_admin),
) -> User:
    return current_user


def _get_authority_token_payload(
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
    if payload.get("role") != "authority":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authority access required.",
        )
    if payload.get("otp_pending"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP verification required.",
        )
    return payload


def get_current_authority(
    payload: dict = Depends(_get_authority_token_payload),
    db: Session = Depends(get_db),
) -> Authority:
    authority_id = payload.get("sub")
    if not authority_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    authority = get_authority_by_id(db, uuid.UUID(str(authority_id)))
    if not authority:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    if not authority.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This authority account has been deactivated.",
        )
    token_drop_point_id = payload.get("drop_point_id")
    if token_drop_point_id and str(authority.drop_point_id) != str(token_drop_point_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    return authority


def _get_supervisor_token_payload(
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
    if payload.get("role") != "supervisor":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Supervisor access required.",
        )
    return payload


def get_current_supervisor(
    payload: dict = Depends(_get_supervisor_token_payload),
    db: Session = Depends(get_db),
) -> "Supervisor":
    from app.models.supervisor import Supervisor
    from app.services.supervisor_service import assigned_drop_point_ids

    supervisor_id = payload.get("sub")
    if not supervisor_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    supervisor = get_supervisor_by_id(db, uuid.UUID(str(supervisor_id)))
    if not supervisor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    if not supervisor.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This supervisor account has been deactivated.",
        )
    if not assigned_drop_point_ids(supervisor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No drop points assigned to this supervisor.",
        )
    token_dp_ids = payload.get("drop_point_ids") or []
    if token_dp_ids:
        token_set = {str(x) for x in token_dp_ids}
        db_set = {str(x) for x in assigned_drop_point_ids(supervisor)}
        if token_set != db_set:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    return supervisor


def assert_authority_drop_point_scope(
    authority: Authority,
    resource_drop_point_id: uuid.UUID | None,
    *,
    resource_exists: bool,
) -> None:
    """Section 16.2 — 403 on mismatch, 404 when resource is outside scope."""
    if not resource_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    if resource_drop_point_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    if authority.drop_point_id != resource_drop_point_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )
