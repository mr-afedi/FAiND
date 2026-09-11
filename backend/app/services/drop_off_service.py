"""
Drop-off confirmation — dual confirm + QR (Section 7.5, Section 9).
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.drop_point import DropPoint
from app.models.item import Item, ItemStatus, ItemType
from app.models.user import User
from app.schemas.drop_off import DropOffInfo, DropOffPhase
from app.services import authority_notification_service, token_service
from app.services.token_service import EscrowAwardResult

logger = logging.getLogger(__name__)

DROP_OFF_REMINDER_HOURS = 24
DROP_OFF_DEADLINE_HOURS = 48
DROP_OFF_UNCONFIRMED_HOURS = 72
DROP_OFF_QR_VALID_HOURS = 24

_ACCEPTS_DROP_OFF_STATUSES = frozenset({ItemStatus.FOUND, ItemStatus.OVERDUE})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_qr_png_data_url(payload: str) -> Optional[str]:
    """PNG data URL for drop-off QR display (Section 9.2)."""
    try:
        import base64
        import io

        import qrcode
    except ImportError:
        logger.warning("qrcode package not installed — QR image omitted; use qr_payload on client")
        return None

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _qr_is_expired(item: Item, now: datetime) -> bool:
    expires_at = item.created_at + timedelta(hours=DROP_OFF_QR_VALID_HOURS)
    return now > expires_at


def ensure_dropoff_qr(item: Item) -> None:
    """Backfill QR for legacy found items still accepting drop-off."""
    if item.dropoff_qr_token_hash or not accepts_drop_off(item):
        return
    assign_dropoff_qr(item)


def _item_age_hours(item: Item, now: datetime) -> float:
    return (now - item.created_at).total_seconds() / 3600.0


def is_dropoff_complete(item: Item) -> bool:
    return item.status == ItemStatus.AT_DROPPOINT


def accepts_drop_off(item: Item) -> bool:
    return item.status in _ACCEPTS_DROP_OFF_STATUSES


def assign_dropoff_qr(item: Item) -> str:
    """Generate single-use drop-off QR at item creation; returns qr_payload."""
    token = secrets.token_urlsafe(32)
    payload = f"faind-drop:{item.id}:{token}"
    item.dropoff_qr_payload = payload
    item.dropoff_qr_token_hash = _hash_token(token)
    return payload


def build_drop_off_info(item: Item) -> DropOffInfo:
    now = _now()
    deadline_48 = item.created_at + timedelta(hours=DROP_OFF_DEADLINE_HOURS)
    deadline_72 = item.created_at + timedelta(hours=DROP_OFF_UNCONFIRMED_HOURS)

    hours_remaining = max(0, int((deadline_48 - now).total_seconds() // 3600))
    hours_until_unconfirmed = max(0, int((deadline_72 - now).total_seconds() // 3600))
    age_hours = _item_age_hours(item, now)

    if item.status == ItemStatus.AT_DROPPOINT:
        phase: DropOffPhase = "at_droppoint"
    elif item.status == ItemStatus.UNCONFIRMED:
        phase = "unconfirmed"
    elif item.status == ItemStatus.OVERDUE:
        phase = "finder_confirmed" if item.finder_dropped_off_at else "overdue"
    elif item.finder_dropped_off_at and not item.authority_received_at:
        phase = "finder_confirmed"
    else:
        phase = "pending"

    can_confirm = (
        accepts_drop_off(item)
        and not item.finder_dropped_off_at
        and not is_dropoff_complete(item)
    )

    qr_payload = None
    qr_image_data_url = None
    if (
        item.dropoff_qr_payload
        and not item.dropoff_qr_consumed_at
        and item.status != ItemStatus.UNCONFIRMED
        and not is_dropoff_complete(item)
        and not _qr_is_expired(item, now)
    ):
        qr_payload = item.dropoff_qr_payload
        qr_image_data_url = generate_qr_png_data_url(qr_payload)

    show_reminder = (
        age_hours >= DROP_OFF_REMINDER_HOURS
        and item.status in (ItemStatus.FOUND, ItemStatus.OVERDUE)
        and not is_dropoff_complete(item)
        and not item.finder_dropped_off_at
    )

    return DropOffInfo(
        hours_remaining=hours_remaining,
        hours_until_unconfirmed=hours_until_unconfirmed,
        dropoff_phase=phase,
        finder_dropped_off_at=item.finder_dropped_off_at,
        authority_received_at=item.authority_received_at,
        can_confirm_drop_off=can_confirm,
        accepts_drop_off=accepts_drop_off(item),
        dropoff_late=bool(item.dropoff_late),
        qr_payload=qr_payload,
        qr_image_data_url=qr_image_data_url,
        qr_consumed=bool(item.dropoff_qr_consumed_at),
        show_dropoff_reminder=show_reminder,
    )


def _apply_late_flag(item: Item, now: datetime) -> None:
    if _item_age_hours(item, now) >= DROP_OFF_DEADLINE_HOURS:
        item.dropoff_late = True


def _get_found_item(
    db: Session,
    item_id: uuid.UUID,
) -> Item:
    item = (
        db.query(Item)
        .options(joinedload(Item.drop_point))
        .filter(Item.id == item_id, Item.item_type == ItemType.FOUND)
        .first()
    )
    if not item or not item.drop_point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
    return item


def _get_found_item_by_tracking_ref(db: Session, tracking_reference: str) -> Item:
    ref = tracking_reference.strip().upper()
    item = (
        db.query(Item)
        .options(joinedload(Item.drop_point))
        .filter(
            Item.tracking_reference == ref,
            Item.item_type == ItemType.FOUND,
        )
        .first()
    )
    if not item or not item.drop_point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
    return item


def _authorize_finder(
    item: Item,
    *,
    current_user: Optional[User] = None,
    tracking_reference: Optional[str] = None,
) -> None:
    if current_user and item.posted_by_id and item.posted_by_id == current_user.id:
        return
    if tracking_reference and item.tracking_reference:
        if item.tracking_reference.upper() == tracking_reference.strip().upper():
            return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


def _reject_invalid_dropoff(item: Item) -> None:
    if item.status == ItemStatus.UNCONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This item is no longer accepting drop-off.",
        )
    if is_dropoff_complete(item):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Drop-off has already been confirmed.",
        )
    if not accepts_drop_off(item):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Drop-off is not available for this item.",
        )


def try_finalize_at_droppoint(
    db: Session, item: Item, drop_point: DropPoint
) -> tuple[bool, Optional[EscrowAwardResult]]:
    """Set AT_DROPPOINT when both dual confirmations are present."""
    if is_dropoff_complete(item):
        return True, None
    if not item.finder_dropped_off_at or not item.authority_received_at:
        return False, None

    now = _now()
    item.status = ItemStatus.AT_DROPPOINT
    item.dropoff_confirmed_at = now
    item.updated_at = now
    from app.services import notification_service

    notification_service.notify_finder_dropoff_complete(db, item=item)
    notification_service.notify_pending_claim_owners_item_ready(
        db, item=item, drop_point=drop_point
    )
    notification_service.notify_interested_parties_item_at_droppoint(
        db, item=item, drop_point=drop_point
    )
    award = token_service.award_drop_off_confirmed(db, item)
    logger.info("drop_off finalized item=%s → AT_DROPPOINT", item.id)
    return True, award


def finder_confirm_drop_off(
    db: Session,
    item: Item,
    *,
    drop_point: DropPoint,
) -> tuple[str, bool, Optional[EscrowAwardResult]]:
    _reject_invalid_dropoff(item)
    now = _now()

    if item.finder_dropped_off_at:
        completed, award = try_finalize_at_droppoint(db, item, drop_point)
        return "You already marked this item as dropped off.", completed, award

    item.finder_dropped_off_at = now
    item.updated_at = now
    _apply_late_flag(item, now)
    authority_notification_service.notify_authority_finder_marked_dropoff(
        db, item=item, drop_point=drop_point
    )

    completed, award = try_finalize_at_droppoint(db, item, drop_point)
    if completed:
        message = "Drop-off confirmed! The item is now at the drop point."
    else:
        message = (
            "Thanks — we recorded your drop-off. Waiting for the drop point "
            "to confirm receipt."
        )
    return message, completed, award


def authority_confirm_received_for_item(
    db: Session,
    item: Item,
) -> tuple[str, bool, Optional[EscrowAwardResult]]:
    """Authority confirms receipt — dual-confirm half (Section 9.1)."""
    drop_point = item.drop_point
    if not drop_point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")

    if item.status == ItemStatus.UNCONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This item is no longer accepting drop-off.",
        )
    if is_dropoff_complete(item):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Drop-off has already been confirmed.",
        )

    now = _now()
    if not item.authority_received_at:
        item.authority_received_at = now
        item.updated_at = now
        _apply_late_flag(item, now)
        authority_notification_service.notify_authority_received_stub(
            db, item=item, drop_point=drop_point
        )

    completed, award = try_finalize_at_droppoint(db, item, drop_point)
    if completed:
        message = "Receipt confirmed. Item is now at the drop point."
    else:
        message = "Receipt recorded. Waiting for the finder to confirm drop-off."
    return message, completed, award


def authority_confirm_received_stub(
    db: Session,
    item_id: uuid.UUID,
) -> tuple[str, bool, Optional[EscrowAwardResult]]:
    """Unauthenticated stub retained for dev/testing — superseded by W7 authority route."""
    item = _get_found_item(db, item_id)
    return authority_confirm_received_for_item(db, item)


def _parse_qr_token(raw: str) -> tuple[Optional[uuid.UUID], str]:
    token = raw.strip()
    item_id: Optional[uuid.UUID] = None
    if token.startswith("faind-drop:"):
        parts = token.split(":")
        if len(parts) >= 3:
            try:
                item_id = uuid.UUID(parts[1])
            except ValueError:
                item_id = None
            token = parts[-1]
    return item_id, token


def redeem_drop_off_qr(db: Session, raw_token: str) -> tuple[str, Item, Optional[EscrowAwardResult]]:
    """Authority scans finder QR — instant AT_DROPPOINT (Section 9.2)."""
    item_id, token = _parse_qr_token(raw_token)
    token_hash = _hash_token(token)
    now = _now()

    query = (
        db.query(Item)
        .options(joinedload(Item.drop_point))
        .filter(
            Item.item_type == ItemType.FOUND,
            Item.dropoff_qr_token_hash == token_hash,
        )
    )
    if item_id is not None:
        query = query.filter(Item.id == item_id)

    item = query.first()
    if not item or not item.drop_point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired QR code.",
        )

    if item.status == ItemStatus.UNCONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This item is no longer accepting drop-off.",
        )
    if is_dropoff_complete(item):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Drop-off has already been confirmed.",
        )
    if item.dropoff_qr_consumed_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This QR code was already used.",
        )
    if _qr_is_expired(item, now):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This QR code has expired.",
        )

    item.dropoff_qr_consumed_at = now
    item.finder_dropped_off_at = item.finder_dropped_off_at or now
    item.authority_received_at = now
    item.status = ItemStatus.AT_DROPPOINT
    item.dropoff_confirmed_at = now
    item.updated_at = now
    _apply_late_flag(item, now)

    from app.services import notification_service

    notification_service.notify_finder_dropoff_complete(db, item=item)
    if item.drop_point:
        notification_service.notify_pending_claim_owners_item_ready(
            db, item=item, drop_point=item.drop_point
        )
    award = token_service.award_drop_off_confirmed(db, item)
    logger.info("drop_off QR redeemed item=%s → AT_DROPPOINT", item.id)
    return "Drop-off confirmed via QR.", item, award


def redeem_drop_off_qr_for_authority(
    db: Session,
    authority: "Authority",
    raw_token: str,
) -> tuple[str, Item, Optional[EscrowAwardResult]]:
    """Authority scans finder QR — scoped to authority drop point (Section 9.2)."""
    item_id, token = _parse_qr_token(raw_token)
    token_hash = _hash_token(token)
    query = db.query(Item).filter(
        Item.item_type == ItemType.FOUND,
        Item.dropoff_qr_token_hash == token_hash,
    )
    if item_id is not None:
        query = query.filter(Item.id == item_id)
    scoped_item = query.first()
    if not scoped_item or not scoped_item.drop_point_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired QR code.",
        )
    if scoped_item.drop_point_id != authority.drop_point_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This QR code belongs to a different drop point.",
        )
    return redeem_drop_off_qr(db, raw_token)


def finder_confirm_by_tracking_ref(
    db: Session, tracking_reference: str
) -> tuple[str, Item, Optional[EscrowAwardResult]]:
    item = _get_found_item_by_tracking_ref(db, tracking_reference)
    _authorize_finder(item, tracking_reference=tracking_reference)
    message, _, award = finder_confirm_drop_off(db, item, drop_point=item.drop_point)
    return message, item, award


def finder_confirm_by_item_id(
    db: Session,
    item_id: uuid.UUID,
    current_user: User,
) -> tuple[str, Item, Optional[EscrowAwardResult]]:
    item = _get_found_item(db, item_id)
    _authorize_finder(item, current_user=current_user)
    message, _, award = finder_confirm_drop_off(db, item, drop_point=item.drop_point)
    return message, item, award
