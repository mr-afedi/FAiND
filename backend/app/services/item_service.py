"""
Item service — business logic for Lost & Found Item Reporting (Features C & D).
Business logic lives here; route handlers only handle request/response.
"""
import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, exists, or_
from sqlalchemy.orm import Session, joinedload

from app.models.campus_zone import CampusZone
from app.models.drop_point import DropPoint
from app.models.item import Item, ItemStatus, ItemType
from app.models.item_return import ItemReturn
from app.schemas.item import PublicReturnedItem, PublicReturnedListResponse
from app.models.user import User, AccountStatus
from app.models.university import University
from app.models.potential_match import PotentialMatch, PotentialMatchStatus
import app.services.matching_service as matching_service
from app.schemas.item import (
    CreateLostItemRequest,
    UpdateLostItemRequest,
    LostItemListItem,
    LostItemListResponse,
    LostItemPublicResponse,
    LostItemOwnerResponse,
    ItemPosterSummary,
    CreateFoundItemRequest,
    UpdateFoundItemRequest,
    FoundItemListItem,
    FoundItemListResponse,
    FoundItemCreateResponse,
    FoundItemTrackResponse,
    BrowseItemPoster,
    BrowseItemCard,
    BrowseListResponse,
    HomepageResponse,
    RecentlyReturnedItem,
)
from app.utils.location_utils import _resolve_location
from app.services import drop_point_service
from app.services import drop_off_service
from app.services import token_service
from app.services.authority_notification_service import notify_authority_found_item_reported
from app.services import claim_service

# Lost items are active for 45 days (Section 21.1)
_LOST_ITEM_ACTIVE_DAYS = 45


# ── Helpers ──────────────────────────────────────────────────────────────────

def _poster_summary(item: Item) -> ItemPosterSummary:
    if item.posted_by:
        return ItemPosterSummary(
            id=item.posted_by.id,
            display_name=item.posted_by.full_name,
            username=item.posted_by.username,
        )
    return ItemPosterSummary(
        id=item.id,
        display_name="Anonymous finder",
        username="anonymous",
    )


def _build_owner_response(
    item: Item,
    db: Session,
    override_status: Optional[ItemStatus] = None,
    *,
    already_submitted: bool = False,
    message: Optional[str] = None,
) -> LostItemOwnerResponse:
    poster = _poster_summary(item)
    return LostItemOwnerResponse(
        id=item.id,
        item_type=item.item_type,
        status=override_status if override_status is not None else item.status,
        category=item.category,
        public_description=item.public_description,
        location_label=item.location_label,
        location_lat=item.location_lat,
        location_lng=item.location_lng,
        date_occurred=item.date_occurred,
        image_urls=item.image_urls or [],
        expiry_date=item.expiry_date,
        extensions_used=item.extensions_used,
        created_at=item.created_at,
        posted_by=poster,
        already_submitted=already_submitted,
        message=message,
    )


def _build_public_response(
    item: Item,
    mask_match_status: bool = False,
    show_as_matched: bool = False,
    viewer_claim=None,
) -> LostItemPublicResponse:
    poster = _poster_summary(item)
    # Section 10 — match/verification statuses are private; only owners see them on their post.
    # show_as_matched=True  → party viewer sees POTENTIAL_MATCH (not under_verification)
    # mask_match_status=True → non-party sees normal open/found feed status
    if show_as_matched:
        visible_status = ItemStatus.POTENTIAL_MATCH
    elif mask_match_status and item.status in (
        ItemStatus.POTENTIAL_MATCH,
        ItemStatus.UNDER_VERIFICATION,
        ItemStatus.UNDER_DISPUTE,
    ):
        visible_status = (
            ItemStatus.OPEN if item.item_type == ItemType.LOST else ItemStatus.FOUND
        )
    elif item.status in (
        ItemStatus.UNDER_VERIFICATION,
        ItemStatus.UNDER_DISPUTE,
    ):
        visible_status = (
            ItemStatus.OPEN if item.item_type == ItemType.LOST else ItemStatus.FOUND
        )
    else:
        visible_status = item.status
    return LostItemPublicResponse(
        id=item.id,
        item_type=item.item_type,
        status=visible_status,
        category=item.category,
        public_description=item.public_description,
        location_label=item.location_label,
        location_lat=item.location_lat,
        location_lng=item.location_lng,
        date_occurred=item.date_occurred,
        image_urls=item.image_urls or [],
        expiry_date=item.expiry_date,
        extensions_used=item.extensions_used,
        created_at=item.created_at,
        posted_by=poster,
        viewer_claim=viewer_claim,
    )


# ── Create ───────────────────────────────────────────────────────────────────

_DUPLICATE_ITEM_MESSAGE = (
    "You have already submitted this item. Please wait before trying again."
)
_DUPLICATE_SUBMIT_WINDOW_SECONDS = 30
_LOST_IDEMPOTENCY_WINDOW_SECONDS = 60
_LOST_IDEMPOTENCY_MESSAGE = "Your item was already submitted successfully"


def _find_recent_lost_item_idempotent(
    db: Session,
    *,
    user_id: uuid.UUID,
    category,
    zone_id: Optional[uuid.UUID],
    window_seconds: int = _LOST_IDEMPOTENCY_WINDOW_SECONDS,
) -> Optional[Item]:
    """Same user + category + location within window → return existing lost item."""
    since = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    q = (
        db.query(Item)
        .filter(
            Item.posted_by_id == user_id,
            Item.item_type == ItemType.LOST,
            Item.category == category,
            Item.created_at >= since,
        )
    )
    if zone_id is None:
        q = q.filter(Item.location_id.is_(None))
    else:
        q = q.filter(Item.location_id == zone_id)
    return q.order_by(Item.created_at.desc()).first()


def _assert_not_duplicate_item_post(
    db: Session,
    *,
    user_id: uuid.UUID,
    item_type: ItemType,
    category,
    public_description: str,
    zone_id: uuid.UUID,
) -> None:
    """Reject identical item posts within 30 seconds (double-submit guard)."""
    since = datetime.now(timezone.utc) - timedelta(seconds=_DUPLICATE_SUBMIT_WINDOW_SECONDS)
    desc_norm = public_description.strip().lower()
    recent = (
        db.query(Item)
        .filter(
            Item.posted_by_id == user_id,
            Item.item_type == item_type,
            Item.category == category,
            Item.location_id == zone_id,
            Item.created_at >= since,
        )
        .all()
    )
    for item in recent:
        if item.public_description.strip().lower() == desc_norm:
            raise ValueError(_DUPLICATE_ITEM_MESSAGE)


def create_lost_item(
    db: Session,
    current_user: User,
    payload: CreateLostItemRequest,
) -> LostItemOwnerResponse:
    # Rate limit guard: max 10 lost/found posts per user per day (Section 30.5)
    # (actual IP-level rate limiting is in the route via slowapi; this is the
    #  per-user-per-day logical guard)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_count = (
        db.query(Item)
        .filter(
            Item.posted_by_id == current_user.id,
            Item.created_at >= today_start,
        )
        .count()
    )
    if daily_count >= 10:
        raise ValueError("You have reached the daily limit of 10 item posts")

    label, lat, lng, zone_id = _resolve_location(db, payload.location_id, current_user.university_id)

    existing = _find_recent_lost_item_idempotent(
        db,
        user_id=current_user.id,
        category=payload.category,
        zone_id=zone_id,
    )
    if existing:
        item = (
            db.query(Item)
            .options(joinedload(Item.posted_by))
            .filter(Item.id == existing.id)
            .one()
        )
        return _build_owner_response(
            item,
            db,
            already_submitted=True,
            message=_LOST_IDEMPOTENCY_MESSAGE,
        )

    expiry = datetime.now(timezone.utc) + timedelta(days=_LOST_ITEM_ACTIVE_DAYS)

    item = Item(
        university_id=current_user.university_id,
        posted_by_id=current_user.id,
        item_type=ItemType.LOST,
        status=ItemStatus.OPEN,
        category=payload.category,
        public_description=payload.public_description,
        location_id=zone_id,
        location_label=label,
        location_lat=lat,
        location_lng=lng,
        date_occurred=payload.date_occurred,
        image_urls=payload.image_urls,
        expiry_date=expiry,
    )
    matching_service.attach_description_embedding(item)
    db.add(item)
    db.commit()

    item = (
        db.query(Item)
        .options(joinedload(Item.posted_by))
        .filter(Item.id == item.id)
        .one()
    )
    return _build_owner_response(item, db)


# ── Read ─────────────────────────────────────────────────────────────────────

def get_item_detail(
    db: Session,
    item_id: uuid.UUID,
    current_user: Optional[User],
) -> LostItemPublicResponse | LostItemOwnerResponse:
    """
    Returns owner response for the item owner; public response for others.
    Archived items visible only to their owner (Section 21.5).
    Match status is masked for viewers who are not a party to the match (Section 10).
    """
    item: Optional[Item] = (
        db.query(Item)
        .options(joinedload(Item.posted_by))
        .filter(Item.id == item_id)
        .first()
    )
    if not item:
        raise LookupError("Item not found")

    is_owner = current_user and item.posted_by_id == current_user.id

    # Archived items are hidden from the entire app (Section 21.5)
    if item.status == ItemStatus.ARCHIVED:
        raise LookupError("Item not found")

    # Look up any live match involving this item — used for both owner and
    # non-owner paths below to determine party membership.
    # Anonymous finders have posted_by_id=None; never treat None as a party id.
    active_match = (
        db.query(PotentialMatch)
        .options(
            joinedload(PotentialMatch.lost_item),
            joinedload(PotentialMatch.found_item),
        )
        .filter(
            PotentialMatch.status.in_([
                PotentialMatchStatus.ACTIVE,
                PotentialMatchStatus.PENDING_REVIEW,
                PotentialMatchStatus.PAUSED,
                PotentialMatchStatus.VERIFIED,
            ]),
            (PotentialMatch.lost_item_id == item.id) | (PotentialMatch.found_item_id == item.id),
        )
        .first()
    )
    is_party = False
    if current_user and active_match:
        lost_poster = active_match.lost_item.posted_by_id if active_match.lost_item else None
        found_poster = active_match.found_item.posted_by_id if active_match.found_item else None
        is_party = (
            current_user.id == lost_poster
            or (found_poster is not None and current_user.id == found_poster)
        )

    if is_owner:
        # Found items stay "found" in the DB even when matched — show Path A match
        # status to the owner.
        override = (
            ItemStatus.POTENTIAL_MATCH
            if active_match
            and is_party
            and matching_service.is_ai_potential_match(active_match)
            else None
        )
        if (
            item.item_type == ItemType.LOST
            and item.status == ItemStatus.POTENTIAL_MATCH
            and override is None
        ):
            override = ItemStatus.OPEN
        return _build_owner_response(item, db, override_status=override)

    # Non-owner: party members always see POTENTIAL_MATCH badge (even on found items
    # whose DB status is "found"). Everyone else gets the masked status.

    viewer_claim = None
    if (
        current_user
        and item.item_type == ItemType.FOUND
        and not is_owner
    ):
        viewer_claim = claim_service.get_viewer_claim_for_found_item(
            db, current_user, item.id
        )

    return _build_public_response(
        item,
        show_as_matched=is_party and active_match is not None,
        mask_match_status=not is_party,
        viewer_claim=viewer_claim,
    )


def list_my_lost_items(
    db: Session,
    current_user: User,
    skip: int = 0,
    limit: int = 20,
) -> LostItemListResponse:
    query = (
        db.query(Item)
        .filter(
            Item.posted_by_id == current_user.id,
            Item.item_type == ItemType.LOST,
            Item.status.notin_([ItemStatus.ARCHIVED, ItemStatus.CLOSED]),
        )
        .order_by(Item.created_at.desc())
    )
    total = query.count()
    items = query.offset(skip).limit(limit).all()

    return LostItemListResponse(
        items=[
            LostItemListItem(
                id=i.id,
                category=i.category,
                status=i.status,
                public_description=i.public_description,
                location_label=i.location_label,
                date_occurred=i.date_occurred,
                image_urls=i.image_urls or [],
                expiry_date=i.expiry_date,
                created_at=i.created_at,
            )
            for i in items
        ],
        total=total,
    )


# ── Update ────────────────────────────────────────────────────────────────────

def update_lost_item(
    db: Session,
    item_id: uuid.UUID,
    current_user: User,
    payload: UpdateLostItemRequest,
) -> LostItemOwnerResponse:
    item: Optional[Item] = (
        db.query(Item)
        .filter(Item.id == item_id, Item.posted_by_id == current_user.id)
        .first()
    )
    if not item:
        raise LookupError("Item not found")

    # Only OPEN items can be edited (Section 4.2)
    if item.status not in (ItemStatus.OPEN, ItemStatus.POTENTIAL_MATCH):
        raise ValueError("Only active items can be edited")

    if payload.category is not None:
        item.category = payload.category
    if payload.public_description is not None:
        item.public_description = payload.public_description
    if payload.date_occurred is not None:
        item.date_occurred = payload.date_occurred
    if payload.image_urls is not None:
        item.image_urls = payload.image_urls
    if payload.location_id is not None:
        label, lat, lng, zone_id = _resolve_location(db, payload.location_id, current_user.university_id)
        item.location_id = zone_id
        item.location_label = label
        item.location_lat = lat
        item.location_lng = lng

    db.commit()

    item = (
        db.query(Item)
        .options(joinedload(Item.posted_by))
        .filter(Item.id == item.id)
        .one()
    )
    return _build_owner_response(item, db)


# ── Soft Delete ───────────────────────────────────────────────────────────────

def delete_lost_item(
    db: Session,
    item_id: uuid.UUID,
    current_user: User,
) -> None:
    """Soft delete — sets status to ARCHIVED (Section 21.5). Never destroys records."""
    item: Optional[Item] = (
        db.query(Item)
        .filter(Item.id == item_id, Item.posted_by_id == current_user.id)
        .first()
    )
    if not item:
        raise LookupError("Item not found")

    if item.admin_locked:
        raise ValueError("This item is locked and cannot be removed")

    if item.status in (ItemStatus.UNDER_DISPUTE, ItemStatus.RETURNED):
        raise ValueError("Items under dispute or already returned cannot be removed")

    item.status = ItemStatus.ARCHIVED
    matching_service.cleanup_on_item_archive(db, item.id)


# ── Extend ────────────────────────────────────────────────────────────────────

def extend_lost_item(
    db: Session,
    item_id: uuid.UUID,
    current_user: User,
) -> LostItemOwnerResponse:
    """Extend expiry by 30 days. Max 2 extensions (Section 21.1)."""
    item: Optional[Item] = (
        db.query(Item)
        .options(joinedload(Item.posted_by))
        .filter(Item.id == item_id, Item.posted_by_id == current_user.id)
        .first()
    )
    if not item:
        raise LookupError("Item not found")

    if item.extensions_used >= 2:
        raise ValueError("Maximum 2 extensions allowed per post")

    if item.status not in (ItemStatus.OPEN, ItemStatus.POTENTIAL_MATCH):
        raise ValueError("Only active items can be extended")

    item.expiry_date = item.expiry_date + timedelta(days=30)
    item.extensions_used += 1
    item.expiry_reminder_sent_at = None
    db.commit()
    db.refresh(item)

    item = (
        db.query(Item)
        .options(joinedload(Item.posted_by))
        .filter(Item.id == item.id)
        .one()
    )
    return _build_owner_response(item, db)


# ═══════════════════════════════════════════════════════════════════════════
# Feature D — Found Item Reporting
# Found items: no private description, image mandatory,
# initial status FOUND, active 21 days (Section 7, Section 21.2).
# ═══════════════════════════════════════════════════════════════════════════

_FOUND_ITEM_ACTIVE_DAYS = 21
_FOUND_EDIT_WINDOW_MINUTES = 30
_TRACKING_REF_ALPHABET = string.ascii_uppercase + string.digits
_FOUND_LOCKED_STATUSES = frozenset({
    ItemStatus.AT_DROPPOINT,
    ItemStatus.UNCONFIRMED,
    ItemStatus.RETURNED,
    ItemStatus.ARCHIVED,
    ItemStatus.CLOSED,
})


def _generate_tracking_reference(db: Session) -> str:
    for _ in range(32):
        ref = "".join(secrets.choice(_TRACKING_REF_ALPHABET) for _ in range(8))
        exists_ref = (
            db.query(Item.id)
            .filter(Item.tracking_reference == ref)
            .first()
        )
        if not exists_ref:
            return ref
    raise RuntimeError("Could not generate a unique tracking reference")


def _found_edit_window_ends_at(item: Item) -> datetime:
    return item.created_at + timedelta(minutes=_FOUND_EDIT_WINDOW_MINUTES)


def _found_item_edit_state(item: Item) -> tuple[bool, int]:
    """Return (can_edit, minutes_remaining)."""
    if item.status in _FOUND_LOCKED_STATUSES:
        return False, 0
    if item.authority_received_at:
        return False, 0
    ends_at = _found_edit_window_ends_at(item)
    now = datetime.now(timezone.utc)
    if now >= ends_at:
        return False, 0
    remaining = int((ends_at - now).total_seconds() // 60) + 1
    return True, max(remaining, 0)


def _resolve_drop_point(
    db: Session,
    *,
    university_id: uuid.UUID,
    location_lat: float,
    location_lng: float,
    override_drop_point_id: Optional[uuid.UUID],
) -> DropPoint:
    if override_drop_point_id:
        point = (
            db.query(DropPoint)
            .filter(
                DropPoint.id == override_drop_point_id,
                DropPoint.university_id == university_id,
            )
            .first()
        )
        if not point:
            raise ValueError("Drop point not found for this university")
        return point

    result = drop_point_service.get_nearest_drop_point(
        db, location_lat, location_lng, university_id
    )
    nearest_id = result["nearest"]["id"]
    point = db.query(DropPoint).filter(DropPoint.id == nearest_id).first()
    if not point:
        raise ValueError("Could not resolve nearest drop point")
    return point


def _build_found_create_response(
    db: Session,
    item: Item,
    drop_point: DropPoint,
    *,
    escrow_token_plain: Optional[str] = None,
) -> FoundItemCreateResponse:
    can_edit, _ = _found_item_edit_state(item)
    ends_at = _found_edit_window_ends_at(item)
    instruction = (
        f"Please drop this item off at {drop_point.name} within 48 hours. "
        "Thank you for helping a fellow student!"
    )
    return FoundItemCreateResponse(
        id=item.id,
        item_type=item.item_type,
        status=item.status,
        category=item.category,
        public_description=item.public_description,
        location_label=item.location_label,
        location_lat=item.location_lat,
        location_lng=item.location_lng,
        date_occurred=item.date_occurred,
        image_urls=item.image_urls or [],
        expiry_date=item.expiry_date,
        extensions_used=item.extensions_used,
        created_at=item.created_at,
        tracking_reference=item.tracking_reference or "",
        drop_point_id=drop_point.id,
        drop_point_name=drop_point.name,
        instruction_message=instruction,
        can_edit=can_edit,
        edit_window_ends_at=ends_at,
        drop_off=drop_off_service.build_drop_off_info(item),
        token_escrow=token_service.build_token_escrow_info(
            db, item, escrow_token_plain=escrow_token_plain
        ),
    )


def _build_found_track_response(
    db: Session,
    item: Item,
    drop_point: DropPoint,
    *,
    escrow_token_plain: Optional[str] = None,
) -> FoundItemTrackResponse:
    can_edit, minutes_remaining = _found_item_edit_state(item)
    data = _build_found_create_response(
        db, item, drop_point, escrow_token_plain=escrow_token_plain
    ).model_dump()
    data["can_edit"] = can_edit
    data["minutes_remaining"] = minutes_remaining
    return FoundItemTrackResponse(**data)


def _authorize_found_item_edit(
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
    raise LookupError("Item not found")


def _apply_found_item_update(
    db: Session,
    item: Item,
    payload: UpdateFoundItemRequest,
    university_id: uuid.UUID,
) -> None:
    can_edit, _ = _found_item_edit_state(item)
    if not can_edit:
        if item.status == ItemStatus.UNCONFIRMED:
            raise ValueError("This item is no longer accepting edits or drop-off")
        if item.status == ItemStatus.AT_DROPPOINT:
            raise ValueError("This item has already been received at the drop point and cannot be edited")
        raise ValueError("The 30-minute edit window has closed")

    if payload.category is not None:
        item.category = payload.category
    if payload.public_description is not None:
        item.public_description = payload.public_description
    if payload.date_occurred is not None:
        item.date_occurred = payload.date_occurred
    if payload.image_urls is not None:
        item.image_urls = payload.image_urls
    if payload.location_id is not None:
        label, lat, lng, zone_id = _resolve_location(db, payload.location_id, university_id)
        if lat is None or lng is None:
            raise ValueError("Campus location must have coordinates for found items")
        item.location_id = zone_id
        item.location_label = label
        item.location_lat = lat
        item.location_lng = lng


def create_found_item(
    db: Session,
    payload: CreateFoundItemRequest,
    current_user: Optional[User] = None,
) -> FoundItemCreateResponse:
    if current_user is not None:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        daily_count = (
            db.query(Item)
            .filter(Item.posted_by_id == current_user.id, Item.created_at >= today_start)
            .count()
        )
        if daily_count >= 10:
            raise ValueError("You have reached the daily limit of 10 item posts")
        university_id = current_user.university_id
    else:
        university_id = None

    zone = (
        db.query(CampusZone)
        .filter(CampusZone.id == payload.location_id, CampusZone.is_active == True)
        .first()
    )
    if not zone:
        raise ValueError("Campus zone not found")
    if university_id is None:
        university_id = zone.university_id

    label, lat, lng, zone_id = _resolve_location(db, payload.location_id, university_id)

    if lat is None or lng is None:
        raise ValueError("A campus location with coordinates is required to suggest a drop point")

    if current_user is not None:
        _assert_not_duplicate_item_post(
            db,
            user_id=current_user.id,
            item_type=ItemType.FOUND,
            category=payload.category,
            public_description=payload.public_description,
            zone_id=zone_id,
        )

    drop_point = _resolve_drop_point(
        db,
        university_id=university_id,
        location_lat=lat,
        location_lng=lng,
        override_drop_point_id=payload.drop_point_id,
    )

    expiry = datetime.now(timezone.utc) + timedelta(days=_FOUND_ITEM_ACTIVE_DAYS)
    tracking_ref = _generate_tracking_reference(db)

    item = Item(
        university_id=university_id,
        posted_by_id=current_user.id if current_user else None,
        item_type=ItemType.FOUND,
        status=ItemStatus.FOUND,
        category=payload.category,
        public_description=payload.public_description,
        location_id=zone_id,
        location_label=label,
        location_lat=lat,
        location_lng=lng,
        drop_point_id=drop_point.id,
        tracking_reference=tracking_ref,
        date_occurred=payload.date_occurred,
        image_urls=payload.image_urls,
        expiry_date=expiry,
    )
    matching_service.attach_description_embedding(item)
    db.add(item)
    db.flush()

    drop_off_service.assign_dropoff_qr(item)

    award = token_service.award_found_item_posted(
        db,
        item,
        user=current_user,
        escrow_token=payload.escrow_token,
    )

    notify_authority_found_item_reported(db, item=item, drop_point=drop_point)

    db.commit()

    item = (
        db.query(Item)
        .options(joinedload(Item.posted_by), joinedload(Item.drop_point))
        .filter(Item.id == item.id)
        .one()
    )
    return _build_found_create_response(
        db,
        item,
        drop_point,
        escrow_token_plain=award.escrow_token,
    )


def get_found_item_by_tracking_reference(
    db: Session,
    tracking_reference: str,
    *,
    escrow_token_plain: Optional[str] = None,
) -> FoundItemTrackResponse:
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
        raise LookupError("Item not found")
    drop_off_service.ensure_dropoff_qr(item)
    db.flush()
    return _build_found_track_response(
        db, item, item.drop_point, escrow_token_plain=escrow_token_plain
    )


def get_found_item_track_by_id(
    db: Session,
    item_id: uuid.UUID,
    *,
    escrow_token_plain: Optional[str] = None,
) -> FoundItemTrackResponse:
    item = (
        db.query(Item)
        .options(joinedload(Item.drop_point))
        .filter(Item.id == item_id, Item.item_type == ItemType.FOUND)
        .first()
    )
    if not item or not item.drop_point:
        raise LookupError("Item not found")
    drop_off_service.ensure_dropoff_qr(item)
    db.flush()
    return _build_found_track_response(
        db, item, item.drop_point, escrow_token_plain=escrow_token_plain
    )


def get_found_item_track_for_owner(
    db: Session,
    item_id: uuid.UUID,
    current_user: User,
) -> FoundItemTrackResponse:
    """Authenticated finder track view — owner or matching tracking ref holder."""
    item = (
        db.query(Item)
        .options(joinedload(Item.drop_point))
        .filter(Item.id == item_id, Item.item_type == ItemType.FOUND)
        .first()
    )
    if not item or not item.drop_point:
        raise LookupError("Item not found")
    if not item.posted_by_id or item.posted_by_id != current_user.id:
        raise LookupError("Item not found")
    return _build_found_track_response(db, item, item.drop_point)


def update_found_item_by_tracking_reference(
    db: Session,
    tracking_reference: str,
    payload: UpdateFoundItemRequest,
) -> FoundItemTrackResponse:
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
        raise LookupError("Item not found")

    _authorize_found_item_edit(item, tracking_reference=ref)
    _apply_found_item_update(db, item, payload, item.university_id)
    db.commit()

    item = (
        db.query(Item)
        .options(joinedload(Item.drop_point))
        .filter(Item.id == item.id)
        .one()
    )
    return _build_found_track_response(db, item, item.drop_point)


def list_my_found_items(
    db: Session,
    current_user: User,
    skip: int = 0,
    limit: int = 20,
) -> FoundItemListResponse:
    query = (
        db.query(Item)
        .filter(
            Item.posted_by_id == current_user.id,
            Item.item_type == ItemType.FOUND,
            Item.status.notin_([ItemStatus.ARCHIVED, ItemStatus.CLOSED]),
        )
        .order_by(Item.created_at.desc())
    )
    total = query.count()
    items = query.offset(skip).limit(limit).all()

    return FoundItemListResponse(
        items=[
            FoundItemListItem(
                id=i.id,
                category=i.category,
                status=i.status,
                public_description=i.public_description,
                location_label=i.location_label,
                date_occurred=i.date_occurred,
                image_urls=i.image_urls or [],
                expiry_date=i.expiry_date,
                created_at=i.created_at,
            )
            for i in items
        ],
        total=total,
    )


def _build_found_response(item: Item) -> LostItemPublicResponse:
    """Found items have no owner-only fields — public response is the owner response."""
    return _build_public_response(item)


def update_found_item(
    db: Session,
    item_id: uuid.UUID,
    current_user: User,
    payload: UpdateFoundItemRequest,
) -> LostItemPublicResponse:
    item: Optional[Item] = (
        db.query(Item)
        .filter(
            Item.id == item_id,
            Item.posted_by_id == current_user.id,
            Item.item_type == ItemType.FOUND,
        )
        .first()
    )
    if not item:
        raise LookupError("Item not found")

    _authorize_found_item_edit(item, current_user=current_user)
    _apply_found_item_update(db, item, payload, current_user.university_id)
    db.commit()

    item = (
        db.query(Item)
        .options(joinedload(Item.posted_by))
        .filter(Item.id == item.id)
        .one()
    )
    return _build_found_response(item)


def delete_found_item(
    db: Session,
    item_id: uuid.UUID,
    current_user: User,
) -> None:
    """Soft delete — sets status to ARCHIVED (Section 21.5)."""
    item: Optional[Item] = (
        db.query(Item)
        .filter(
            Item.id == item_id,
            Item.posted_by_id == current_user.id,
            Item.item_type == ItemType.FOUND,
        )
        .first()
    )
    if not item:
        raise LookupError("Item not found")
    if item.admin_locked:
        raise ValueError("This item is locked and cannot be removed")
    if item.status in (ItemStatus.UNDER_DISPUTE, ItemStatus.RETURNED):
        raise ValueError("Items under dispute or already returned cannot be removed")

    item.status = ItemStatus.ARCHIVED
    matching_service.cleanup_on_item_archive(db, item.id)


def extend_found_item(
    db: Session,
    item_id: uuid.UUID,
    current_user: User,
) -> LostItemPublicResponse:
    """Extend expiry by 30 days. Max 2 extensions (Section 21.2)."""
    item: Optional[Item] = (
        db.query(Item)
        .options(joinedload(Item.posted_by))
        .filter(
            Item.id == item_id,
            Item.posted_by_id == current_user.id,
            Item.item_type == ItemType.FOUND,
        )
        .first()
    )
    if not item:
        raise LookupError("Item not found")
    if item.extensions_used >= 2:
        raise ValueError("Maximum 2 extensions allowed per post")
    if item.status not in (ItemStatus.FOUND, ItemStatus.POTENTIAL_MATCH):
        raise ValueError("Only active found items can be extended")

    item.expiry_date = item.expiry_date + timedelta(days=30)
    item.extensions_used += 1
    item.expiry_reminder_sent_at = None
    db.commit()

    item = (
        db.query(Item)
        .options(joinedload(Item.posted_by))
        .filter(Item.id == item.id)
        .one()
    )
    return _build_found_response(item)


# ── Public Browse (Feature F) ─────────────────────────────────────────────────

# Statuses visible on the public feed (excludes returned/archived/closed/expired)
_VISIBLE_STATUSES = [
    ItemStatus.OPEN,
    ItemStatus.FOUND,
    ItemStatus.OVERDUE,
    ItemStatus.AT_DROPPOINT,
    ItemStatus.POTENTIAL_MATCH,
    ItemStatus.UNDER_CLAIM_REVIEW,
    ItemStatus.UNDER_VERIFICATION,
    ItemStatus.UNDER_DISPUTE,
]

_TERMINAL_PUBLIC_STATUSES = (
    ItemStatus.RETURNED,
    ItemStatus.ARCHIVED,
    ItemStatus.CLOSED,
    ItemStatus.EXPIRED,
)


def _public_feed_filters():
    """Shared filters for homepage and browse — hide returned and terminal items."""
    completed_return = exists().where(
        and_(
            ItemReturn.returned_at.isnot(None),
            or_(
                ItemReturn.lost_item_id == Item.id,
                ItemReturn.found_item_id == Item.id,
            ),
        )
    )
    return (
        Item.status.in_(_VISIBLE_STATUSES),
        Item.status.notin_(_TERMINAL_PUBLIC_STATUSES),
        ~completed_return,
        Item.hidden_by_suspension == False,
        or_(
            Item.posted_by_id.is_(None),
            User.status == AccountStatus.ACTIVE,
        ),
    )


def _build_browse_card(
    item: Item,
    viewer_matched_ids: Optional[set] = None,
    viewer_claim=None,
) -> BrowseItemCard:
    if item.posted_by:
        poster = BrowseItemPoster(
            id=item.posted_by.id,
            username=item.posted_by.username,
            display_name=item.posted_by.full_name or item.posted_by.username,
        )
    else:
        poster = BrowseItemPoster(
            id=item.id,
            username="anonymous",
            display_name="Anonymous finder",
        )
    # Show POTENTIAL_MATCH to the two parties involved in a match, on BOTH items
    # (lost item and found item). The found item's DB status stays "found" but
    # parties should still see the badge. Non-parties never see POTENTIAL_MATCH.
    is_party = (
        bool(viewer_matched_ids and item.id in viewer_matched_ids)
        and item.status not in _TERMINAL_PUBLIC_STATUSES
    )
    if is_party:
        public_status = ItemStatus.POTENTIAL_MATCH
    elif item.status in (
        ItemStatus.POTENTIAL_MATCH,
        ItemStatus.UNDER_VERIFICATION,
        ItemStatus.UNDER_DISPUTE,
        ItemStatus.UNDER_CLAIM_REVIEW,
    ):
        public_status = (
            ItemStatus.OPEN if item.item_type == ItemType.LOST else ItemStatus.FOUND
        )
    else:
        public_status = item.status
    return BrowseItemCard(
        id=item.id,
        item_type=item.item_type,
        status=public_status,
        category=item.category,
        public_description=item.public_description,
        location_label=item.location_label,
        date_occurred=item.date_occurred,
        image_urls=item.image_urls or [],
        created_at=item.created_at,
        updated_at=item.updated_at,
        posted_by=poster,
        viewer_claim=viewer_claim,
    )


def browse_items(
    db: Session,
    item_type: Optional[ItemType] = None,
    categories: Optional[list] = None,
    location_id: Optional[uuid.UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    statuses: Optional[list] = None,
    q: Optional[str] = None,
    sort: str = "newest",
    skip: int = 0,
    limit: int = 20,
    viewer_matched_ids: Optional[set] = None,
    viewer_user: Optional[User] = None,
) -> BrowseListResponse:
    """
    Public browse feed — no auth required.
    Suspended users' items are excluded (Section 4.7).
    """
    query = (
        db.query(Item)
        .outerjoin(Item.posted_by)
        .options(joinedload(Item.posted_by))
        .filter(*_public_feed_filters())
    )

    if item_type:
        query = query.filter(Item.item_type == item_type)
    if categories:
        query = query.filter(Item.category.in_(categories))
    if location_id:
        query = query.filter(Item.location_id == location_id)
    if date_from:
        query = query.filter(Item.date_occurred >= date_from)
    if date_to:
        query = query.filter(Item.date_occurred <= date_to)
    if statuses:
        query = query.filter(Item.status.in_(statuses))
    if q and q.strip():
        query = query.filter(Item.public_description.ilike(f"%{q.strip()}%"))

    total = query.count()

    if sort == "oldest":
        query = query.order_by(Item.created_at.asc())
    elif sort == "activity":
        query = query.order_by(Item.updated_at.desc())
    else:
        query = query.order_by(Item.created_at.desc())

    items = query.offset(skip).limit(limit).all()

    found_ids = [i.id for i in items if i.item_type == ItemType.FOUND]
    viewer_claims = claim_service.get_viewer_claims_for_found_items(
        db, viewer_user, found_ids
    )

    return BrowseListResponse(
        items=[
            _build_browse_card(
                i,
                viewer_matched_ids,
                viewer_claim=viewer_claims.get(i.id),
            )
            for i in items
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


def get_homepage_data(
    db: Session,
    viewer_matched_ids: Optional[set] = None,
    viewer_user: Optional[User] = None,
) -> HomepageResponse:
    """
    Lightweight homepage snapshot — 5 latest lost, 5 latest found,
    anonymous resolved items from past 7 days (Section 24.1).
    """
    def _active_query(type_filter: ItemType):
        return (
            db.query(Item)
            .outerjoin(Item.posted_by)
            .options(joinedload(Item.posted_by))
            .filter(
                Item.item_type == type_filter,
                *_public_feed_filters(),
            )
            .order_by(Item.created_at.desc())
            .limit(5)
            .all()
        )

    latest_lost = _active_query(ItemType.LOST)
    latest_found = _active_query(ItemType.FOUND)
    found_ids = [i.id for i in latest_found]
    viewer_claims = claim_service.get_viewer_claims_for_found_items(
        db, viewer_user, found_ids
    )

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    returned_filter = (
        ItemReturn.returned_at.isnot(None),
        ItemReturn.returned_at >= seven_days_ago,
    )
    recently_returned_count = (
        db.query(ItemReturn)
        .join(Item, Item.id == ItemReturn.found_item_id)
        .filter(*returned_filter, Item.status == ItemStatus.RETURNED)
        .count()
    )
    recently_returned_rows = (
        db.query(ItemReturn, Item, University)
        .join(Item, Item.id == ItemReturn.found_item_id)
        .join(University, University.id == ItemReturn.university_id)
        .filter(*returned_filter, Item.status == ItemStatus.RETURNED)
        .order_by(ItemReturn.returned_at.desc())
        .limit(6)
        .all()
    )
    recently_returned = [
        RecentlyReturnedItem(
            id=record.id,
            category=found_item.category,
            returned_at=record.returned_at,
            university_short_name=university.short_name,
        )
        for record, found_item, university in recently_returned_rows
    ]

    return HomepageResponse(
        latest_lost=[_build_browse_card(i, viewer_matched_ids) for i in latest_lost],
        latest_found=[
            _build_browse_card(
                i,
                viewer_matched_ids,
                viewer_claim=viewer_claims.get(i.id),
            )
            for i in latest_found
        ],
        recently_returned=recently_returned,
        recently_returned_count=recently_returned_count,
    )


def _public_returned_item_name(item: Item) -> str:
    desc = (item.public_description or "").strip()
    if desc:
        return desc[:80] + ("…" if len(desc) > 80 else "")
    cat = item.category.value.replace("_", " ").title()
    return cat


def list_public_returned_items(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
) -> PublicReturnedListResponse:
    """Anonymous returned items for the past 7 days (Section 16.6)."""
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    base = (
        db.query(ItemReturn, Item, University)
        .join(Item, Item.id == ItemReturn.found_item_id)
        .join(University, University.id == ItemReturn.university_id)
        .filter(
            ItemReturn.returned_at.isnot(None),
            ItemReturn.returned_at >= seven_days_ago,
            Item.status == ItemStatus.RETURNED,
        )
    )
    total = base.count()
    rows = (
        base.order_by(ItemReturn.returned_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    items = [
        PublicReturnedItem(
            id=record.id,
            category=found_item.category,
            item_name="",
            returned_at=record.returned_at,
            university_short_name=university.short_name,
        )
        for record, found_item, university in rows
    ]
    return PublicReturnedListResponse(items=items, total=total)
