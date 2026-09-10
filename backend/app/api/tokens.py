"""
Token escrow API — Section 9.3 / 12.2 (W5).
"""
from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.config import get_settings
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.schemas.token import (
    EscrowClaimLoginRequest,
    EscrowClaimLoginResponse,
    EscrowClaimMeRequest,
    EscrowClaimRegisterRequest,
    EscrowClaimResponse,
    EscrowDiscardRequest,
    EscrowStatusResponse,
)
from app.services import auth_service, token_service

settings = get_settings()
router = APIRouter(prefix="/tokens", tags=["tokens"])
limiter = Limiter(key_func=get_remote_address)

REFRESH_COOKIE_NAME = "faind_refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/",
    )


@router.get("/escrow/status", response_model=EscrowStatusResponse)
def get_escrow_status(
    escrow_token: str = Query(..., min_length=16, max_length=128),
    db: Session = Depends(get_db),
):
    info = token_service.get_escrow_status(db, escrow_token)
    return EscrowStatusResponse(escrow=info)


@router.post("/escrow/discard", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
def discard_escrow(
    request: Request,
    payload: EscrowDiscardRequest,
    db: Session = Depends(get_db),
):
    token_service.discard_escrow(db, payload.escrow_token)
    db.commit()


@router.post("/escrow/claim/me", response_model=EscrowClaimResponse)
@limiter.limit("10/minute")
def claim_escrow_me(
    request: Request,
    payload: EscrowClaimMeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total = token_service.claim_escrow_for_user(
        db,
        plain_token=payload.escrow_token,
        user=current_user,
    )
    db.commit()
    return EscrowClaimResponse(
        message=f"Claimed {total} tokens — they're in your account now!",
        tokens_claimed=total,
    )


@router.post("/escrow/claim/login", response_model=EscrowClaimLoginResponse)
@limiter.limit("10/minute")
def claim_escrow_login(
    request: Request,
    response: Response,
    payload: EscrowClaimLoginRequest,
    db: Session = Depends(get_db),
):
    user, total = token_service.claim_escrow_for_login(
        db,
        plain_token=payload.escrow_token,
        email=payload.email,
        password=payload.password,
    )
    ua = request.headers.get("user-agent")
    ip = get_remote_address(request)
    access_token, refresh_token = auth_service.create_session(db, user, ua, ip)
    db.commit()
    _set_refresh_cookie(response, refresh_token)
    return EscrowClaimLoginResponse(
        message=f"Claimed {total} tokens — welcome back!",
        tokens_claimed=total,
        access_token=access_token,
    )


@router.post("/escrow/claim/register", response_model=EscrowClaimResponse)
@limiter.limit("10/minute")
async def claim_escrow_register(
    request: Request,
    payload: EscrowClaimRegisterRequest,
    db: Session = Depends(get_db),
):
    register_data = RegisterRequest.model_validate(
        payload.model_dump(exclude={"escrow_token"})
    )
    user, total = await token_service.claim_escrow_for_register(
        db,
        plain_token=payload.escrow_token,
        data=register_data,
    )
    db.commit()
    return EscrowClaimResponse(
        message=(
            f"Account created and {total} tokens credited. "
            "Please check your email to verify your account."
        ),
        tokens_claimed=total,
    )
