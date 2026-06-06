"""
TippingService — Paystack appreciation payments (Section 20).

Rules:
- Only lost owner can initiate tips within the 7-day window.
- Webhook signature verification required before marking success.
- Amounts encrypted at rest; never returned in public item/profile APIs.
- Tips do not affect trust score.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.tip_payment import TipPayment, TipPaymentStatus
from app.models.user import User
from app.models.item_return import ItemReturn
from app.services import returned_items_service, notification_service
from app.utils.encryption import encrypt, decrypt

logger = logging.getLogger(__name__)

PAYSTACK_BASE = "https://api.paystack.co"
APPRECIATION_SUMMARY = "The owner expressed appreciation to the finder."
ALREADY_SENT_DETAIL = "Appreciation has already been sent for this return."
STALE_PENDING_HOURS = 1


def paystack_configured() -> bool:
    s = get_settings()
    return bool(s.PAYSTACK_SECRET_KEY and s.PAYSTACK_PUBLIC_KEY)


def count_tips_received(db: Session, user_id: uuid.UUID) -> int:
    return (
        db.query(TipPayment)
        .filter(
            TipPayment.receiver_id == user_id,
            TipPayment.status == TipPaymentStatus.SUCCESS,
        )
        .count()
    )


def _amount_to_pesewas(amount_ghs: Decimal) -> int:
    return int((amount_ghs * 100).quantize(Decimal("1")))


def _reference_for_tip(tip_id: uuid.UUID) -> str:
    return f"faind-tip-{tip_id.hex}"


def _paystack_payment_succeeded(verified: dict) -> bool:
    status = (verified.get("status") or "").lower()
    return status in ("success", "successful") or bool(verified.get("paid_at"))


def _sync_appreciation_from_success_tip(db: Session, record: ItemReturn) -> bool:
    """Heal return row when a successful tip exists but appreciation_sent_at was not set."""
    if record.appreciation_sent_at:
        return False
    tip = (
        db.query(TipPayment)
        .filter(
            TipPayment.return_id == record.id,
            TipPayment.status == TipPaymentStatus.SUCCESS,
        )
        .order_by(TipPayment.paid_at.desc())
        .first()
    )
    if not tip:
        return False
    record.appreciation_sent_at = tip.paid_at or tip.created_at
    record.appreciation_skipped_until = None
    if not record.summary_note:
        record.summary_note = APPRECIATION_SUMMARY
    db.flush()
    return True


def _raise_already_sent() -> None:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=ALREADY_SENT_DETAIL,
    )


def _assert_no_duplicate_tip(
    db: Session, record: ItemReturn, return_id: uuid.UUID, now: datetime
) -> None:
    """Block a second payment — reconcile pending tips with Paystack first."""
    if _sync_appreciation_from_success_tip(db, record):
        db.commit()
        db.refresh(record)
    if record.appreciation_sent_at:
        _raise_already_sent()

    if (
        db.query(TipPayment)
        .filter(
            TipPayment.return_id == return_id,
            TipPayment.status == TipPaymentStatus.SUCCESS,
        )
        .first()
    ):
        if _sync_appreciation_from_success_tip(db, record):
            db.commit()
            db.refresh(record)
        _raise_already_sent()

    pending_tips = (
        db.query(TipPayment)
        .filter(
            TipPayment.return_id == return_id,
            TipPayment.status == TipPaymentStatus.PENDING,
        )
        .order_by(TipPayment.created_at.asc())
        .all()
    )
    for tip in pending_tips:
        try:
            verified = _paystack_verify_transaction(tip.paystack_reference)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A payment is already in progress for this return.",
            ) from None

        if _paystack_payment_succeeded(verified):
            _complete_tip_if_paid(db, tip)
            db.refresh(record)
            _raise_already_sent()

        created = tip.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if now - created < timedelta(hours=STALE_PENDING_HOURS):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A payment is already in progress for this return.",
            )

        tip.status = TipPaymentStatus.FAILED
        db.flush()


def initialize_tip_payment(
    db: Session,
    *,
    return_id: uuid.UUID,
    sender: User,
    amount_ghs: Decimal,
) -> dict:
    if not paystack_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Appreciation payments are not configured. Contact support.",
        )

    record = returned_items_service._get_return_for_user(db, return_id, sender)
    if sender.id != record.lost_owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the lost item owner can send appreciation.",
        )

    now = datetime.now(timezone.utc)
    if record.tip_frozen:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appreciation is frozen while this return is under dispute.",
        )

    _assert_no_duplicate_tip(db, record, return_id, now)

    if record.appreciation_sent_at:
        _raise_already_sent()

    if not returned_items_service.tipping_window_open(record, now):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The appreciation window is not open.",
        )

    tip_id = uuid.uuid4()
    reference = _reference_for_tip(tip_id)
    tip = TipPayment(
        id=tip_id,
        university_id=record.university_id,
        return_id=return_id,
        sender_id=record.lost_owner_id,
        receiver_id=record.found_owner_id,
        amount_encrypted=encrypt(str(amount_ghs)),
        currency="GHS",
        paystack_reference=reference,
        status=TipPaymentStatus.PENDING,
    )
    db.add(tip)
    db.flush()

    settings = get_settings()
    callback_url = f"{settings.FRONTEND_URL.rstrip('/')}/returns/{return_id}?tip_verify=1&reference={reference}"

    payload = {
        "email": sender.email,
        "amount": _amount_to_pesewas(amount_ghs),
        "currency": "GHS",
        "reference": reference,
        "callback_url": callback_url,
        "metadata": {
            "return_id": str(return_id),
            "tip_id": str(tip.id),
            "custom_fields": [
                {"display_name": "Return ID", "variable_name": "return_id", "value": str(return_id)},
            ],
        },
    }

    try:
        data = _paystack_post("/transaction/initialize", payload)
    except HTTPException:
        tip.status = TipPaymentStatus.FAILED
        db.commit()
        raise

    auth_url = data.get("authorization_url")
    if not auth_url:
        tip.status = TipPaymentStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment provider did not return a checkout URL.",
        )

    db.commit()
    db.refresh(tip)

    return {
        "tip_id": tip.id,
        "paystack_reference": reference,
        "authorization_url": auth_url,
        "public_key": settings.PAYSTACK_PUBLIC_KEY,
        "amount_ghs": str(amount_ghs),
    }


def verify_tip_by_reference(db: Session, reference: str, user: User) -> dict:
    """Client callback verification — still confirms with Paystack server-side."""
    tip = _get_tip_by_reference(db, reference)
    if tip.sender_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return _complete_tip_if_paid(db, tip)


def handle_paystack_webhook(db: Session, body: bytes, signature: str | None) -> dict:
    if not signature or not _verify_signature(body, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature.")

    try:
        event = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON.")

    event_type = event.get("event")
    data = event.get("data") or {}
    reference = data.get("reference")

    if event_type != "charge.success" or not reference:
        return {"status": "ignored"}

    tip = (
        db.query(TipPayment)
        .filter(TipPayment.paystack_reference == reference)
        .first()
    )
    if not tip:
        logger.warning("Paystack webhook for unknown reference: %s", reference)
        return {"status": "ignored"}

    if tip.status == TipPaymentStatus.SUCCESS:
        return {"status": "already_processed"}

    return _complete_tip_if_paid(db, tip)


def _complete_tip_if_paid(db: Session, tip: TipPayment) -> dict:
    if tip.status == TipPaymentStatus.SUCCESS:
        return {
            "status": "success",
            "message": "Appreciation was already recorded.",
            "return_id": tip.return_id,
        }

    record = db.query(ItemReturn).filter(ItemReturn.id == tip.return_id).first()
    other_success = (
        db.query(TipPayment)
        .filter(
            TipPayment.return_id == tip.return_id,
            TipPayment.status == TipPaymentStatus.SUCCESS,
            TipPayment.id != tip.id,
        )
        .first()
    )
    if other_success or (record and record.appreciation_sent_at):
        tip.status = TipPaymentStatus.FAILED
        db.commit()
        return {
            "status": "success",
            "message": "Appreciation was already recorded.",
            "return_id": tip.return_id,
        }

    verified = _paystack_verify_transaction(tip.paystack_reference)
    if not _paystack_payment_succeeded(verified):
        return {
            "status": "pending",
            "message": "Payment not completed yet.",
            "return_id": tip.return_id,
        }

    paid_amount_pesewas = verified.get("amount")
    expected_pesewas = _amount_to_pesewas(Decimal(decrypt(tip.amount_encrypted)))
    if paid_amount_pesewas is not None and int(paid_amount_pesewas) != expected_pesewas:
        logger.error(
            "Paystack amount mismatch for %s: expected %s got %s",
            tip.paystack_reference,
            expected_pesewas,
            paid_amount_pesewas,
        )
        tip.status = TipPaymentStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount mismatch.",
        )

    now = datetime.now(timezone.utc)
    tip.status = TipPaymentStatus.SUCCESS
    tip.paid_at = now

    if record and not record.appreciation_sent_at:
        record.appreciation_sent_at = now
        record.appreciation_skipped_until = None
        record.summary_note = APPRECIATION_SUMMARY

        notification_service.notify_appreciation_received(
            db,
            finder_id=tip.receiver_id,
            return_id=tip.return_id,
        )
        notification_service.notify_appreciation_sent(
            db,
            owner_id=tip.sender_id,
            return_id=tip.return_id,
        )

    db.commit()
    return {
        "status": "success",
        "message": "Thank you! Your appreciation was sent successfully.",
        "return_id": tip.return_id,
    }


def list_sent_tips(db: Session, user: User) -> list[dict]:
    rows = (
        db.query(TipPayment)
        .filter(TipPayment.sender_id == user.id)
        .order_by(TipPayment.created_at.desc())
        .limit(50)
        .all()
    )
    return [_serialize_tip_for_user(db, t, user, as_sender=True) for t in rows]


def list_received_tips(db: Session, user: User) -> list[dict]:
    rows = (
        db.query(TipPayment)
        .filter(
            TipPayment.receiver_id == user.id,
            TipPayment.status == TipPaymentStatus.SUCCESS,
        )
        .order_by(TipPayment.created_at.desc())
        .limit(50)
        .all()
    )
    return [_serialize_tip_for_user(db, t, user, as_sender=False) for t in rows]


def admin_get_tip_for_return(db: Session, return_id: uuid.UUID) -> TipPayment:
    tip = (
        db.query(TipPayment)
        .filter(
            TipPayment.return_id == return_id,
            TipPayment.status == TipPaymentStatus.SUCCESS,
        )
        .order_by(TipPayment.paid_at.desc())
        .first()
    )
    if not tip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No successful tip found for this return.",
        )
    return tip


def admin_tip_detail(db: Session, tip: TipPayment) -> dict:
    sender = db.query(User).filter(User.id == tip.sender_id).first()
    receiver = db.query(User).filter(User.id == tip.receiver_id).first()
    return {
        "tip_id": tip.id,
        "return_id": tip.return_id,
        "amount_ghs": decrypt(tip.amount_encrypted),
        "currency": tip.currency,
        "status": tip.status.value,
        "paystack_reference": tip.paystack_reference,
        "sender_email": sender.email if sender else "",
        "receiver_email": receiver.email if receiver else "",
        "paid_at": tip.paid_at,
        "created_at": tip.created_at,
    }


def _serialize_tip_for_user(
    db: Session, tip: TipPayment, viewer: User, *, as_sender: bool
) -> dict:
    other_id = tip.receiver_id if as_sender else tip.sender_id
    other = db.query(User).filter(User.id == other_id).first()
    amount = decrypt(tip.amount_encrypted) if tip.status == TipPaymentStatus.SUCCESS else "—"
    if tip.status != TipPaymentStatus.SUCCESS and as_sender:
        try:
            amount = decrypt(tip.amount_encrypted)
        except Exception:
            amount = "—"
    return {
        "tip_id": tip.id,
        "return_id": tip.return_id,
        "amount_ghs": amount,
        "currency": tip.currency,
        "status": tip.status.value,
        "paid_at": tip.paid_at,
        "created_at": tip.created_at,
        "counterparty_display_name": other.full_name if other else "User",
    }


def _get_tip_by_reference(db: Session, reference: str) -> TipPayment:
    tip = (
        db.query(TipPayment)
        .filter(TipPayment.paystack_reference == reference)
        .first()
    )
    if not tip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")
    return tip


def _paystack_headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def _paystack_post(path: str, payload: dict) -> dict:
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{PAYSTACK_BASE}{path}",
            json=payload,
            headers=_paystack_headers(),
        )
    return _parse_paystack_response(resp)


def _paystack_verify_transaction(reference: str) -> dict:
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{PAYSTACK_BASE}/transaction/verify/{reference}",
            headers=_paystack_headers(),
        )
    data = _parse_paystack_response(resp)
    return data.get("data") or {}


def _parse_paystack_response(resp: httpx.Response) -> dict[str, Any]:
    try:
        body = resp.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid response from payment provider.",
        )
    if not resp.is_success or not body.get("status"):
        message = body.get("message", "Payment provider error.")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=message)
    return body.get("data") or body


def _verify_signature(body: bytes, signature: str) -> bool:
    settings = get_settings()
    secret = settings.PAYSTACK_SECRET_KEY.encode("utf-8")
    computed = hmac.new(secret, body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, signature)
