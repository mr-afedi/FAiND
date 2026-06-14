"""
Item service — business logic for Lost & Found Item Reporting (Features C & D).
Business logic lives here; route handlers only handle request/response.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, exists, or_
from sqlalchemy.orm import Session, joinedload

from app.models.item import Item, ItemHiddenQuestion, ItemStatus, ItemType
from app.models.item_return import ItemReturn
from app.schemas.item import PublicReturnedItem, PublicReturnedListResponse
from app.models.user import User, AccountStatus
from app.models.university import University
from app.models.potential_match import PotentialMatch, PotentialMatchStatus
import app.services.trust_service as trust_service
import app.services.matching_service as matching_service
from app.schemas.item import (
    CheckHiddenAnswersRequest,
    CreateLostItemRequest,
    HiddenQuestionInput,
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
    BrowseItemPoster,
    BrowseItemCard,
    BrowseListResponse,
    HomepageResponse,
)
from app.utils.encryption import encrypt
from app.utils.location_utils import _resolve_location
from app.services import path_b_service, path_c_service

# Lost items are active for 45 days (Section 21.1)
_LOST_ITEM_ACTIVE_DAYS = 45


# ── Helpers ──────────────────────────────────────────────────────────────────

_OBVIOUS_ANSWER_THRESHOLD = 0.65


def hidden_answer_warnings(
    public_description: str,
    hidden_questions: list[HiddenQuestionInput],
) -> list[str]:
    """Warn when a hidden answer is too similar to the public description (V4.3 §6.1)."""
    warnings: list[str] = []
    for idx, q in enumerate(hidden_questions, start=1):
        sim = matching_service.description_similarity(public_description, q.answer)
        if sim >= _OBVIOUS_ANSWER_THRESHOLD:
            warnings.append(
                f"Question {idx}: This answer might be too obvious. "
                "Consider asking something more specific."
            )
    return warnings


def check_hidden_answers(payload: CheckHiddenAnswersRequest) -> list[str]:
    return hidden_answer_warnings(payload.public_description, payload.hidden_questions)


def _build_owner_response(
    item: Item,
    db: Session,
    override_status: Optional[ItemStatus] = None,
    warnings: Optional[list[str]] = None,
    *,
    already_submitted: bool = False,
    message: Optional[str] = None,
) -> LostItemOwnerResponse:
    poster = ItemPosterSummary(
        id=item.posted_by.id,
        display_name=item.posted_by.full_name,
        username=item.posted_by.username,
        trust_tier=trust_service.get_trust_tier(item.posted_by.trust_score),
    )
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
        warnings=warnings or [],
        already_submitted=already_submitted,
        message=message,
    )


def _build_public_response(
    item: Item,
    mask_match_status: bool = False,
    show_as_matched: bool = False,
    viewer_path_b_status: Optional[str] = None,
    viewer_path_b_conversation_id: Optional[uuid.UUID] = None,
    viewer_path_c_status: Optional[str] = None,
    viewer_path_c_conversation_id: Optional[uuid.UUID] = None,
) -> LostItemPublicResponse:
    poster = ItemPosterSummary(
        id=item.posted_by.id,
        display_name=item.posted_by.full_name,
        username=item.posted_by.username,
        trust_tier=trust_service.get_trust_tier(item.posted_by.trust_score),
    )
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
        viewer_path_b_status=viewer_path_b_status,
        viewer_path_b_conversation_id=viewer_path_b_conversation_id,
        viewer_path_c_status=viewer_path_c_status,
        viewer_path_c_conversation_id=viewer_path_c_conversation_id,
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

    warnings = hidden_answer_warnings(payload.public_description, payload.hidden_questions)

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
    db.add(item)
    db.flush()

    for idx, q in enumerate(payload.hidden_questions, start=1):
        db.add(
            ItemHiddenQuestion(
                item_id=item.id,
                question=encrypt(q.question),
                answer=encrypt(q.answer),
                position=idx,
            )
        )

    db.commit()

    item = (
        db.query(Item)
        .options(joinedload(Item.posted_by))
        .filter(Item.id == item.id)
        .one()
    )
    return _build_owner_response(item, db, warnings=warnings)


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
        .options(joinedload(Item.posted_by), joinedload(Item.hidden_questions))
        .filter(Item.id == item_id)
        .first()
    )
    if not item:
        raise LookupError("Item not found")

    is_owner = current_user and item.posted_by_id == current_user.id

    # Archived items are hidden from the entire app (Section 21.5)
    if item.status == ItemStatus.ARCHIVED:
        raise LookupError("Item not found")

    # Look up any active match involving this item — used for both owner and
    # non-owner paths below to determine party membership.
    active_match = (
        db.query(PotentialMatch)
        .options(
            joinedload(PotentialMatch.lost_item),
            joinedload(PotentialMatch.found_item),
        )
        .filter(
            PotentialMatch.status.in_([
                PotentialMatchStatus.ACTIVE,
                PotentialMatchStatus.PAUSED,
            ]),
            (PotentialMatch.lost_item_id == item.id) | (PotentialMatch.found_item_id == item.id),
        )
        .first()
    )
    party_ids = (
        {active_match.lost_item.posted_by_id, active_match.found_item.posted_by_id}
        if active_match else set()
    )

    if is_owner:
        # Found items stay "found" in the DB even when matched — show Path A match
        # status to the owner. Lost posts stay OPEN for Path B/C (potential_match is Path A only).
        override = (
            ItemStatus.POTENTIAL_MATCH
            if active_match
            and current_user.id in party_ids
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
    is_party = current_user is not None and current_user.id in party_ids

    path_b_status: Optional[str] = None
    path_b_conv: Optional[uuid.UUID] = None
    path_c_status: Optional[str] = None
    path_c_conv: Optional[uuid.UUID] = None
    if current_user and item.posted_by_id != current_user.id:
        if item.item_type == ItemType.LOST:
            path_b_status, path_b_conv = path_b_service.resolve_viewer_path_b_status(
                db, current_user.id, item.id
            )
        elif item.item_type == ItemType.FOUND:
            path_c_status, path_c_conv = path_c_service.resolve_viewer_path_c_status(
                db, current_user.id, item.id
            )

    return _build_public_response(
        item,
        show_as_matched=is_party and active_match is not None,
        mask_match_status=not is_party,
        viewer_path_b_status=path_b_status,
        viewer_path_b_conversation_id=path_b_conv,
        viewer_path_c_status=path_c_status,
        viewer_path_c_conversation_id=path_c_conv,
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
            Item.path_c_bridge == False,
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
        .options(joinedload(Item.posted_by), joinedload(Item.hidden_questions))
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
        .options(joinedload(Item.posted_by), joinedload(Item.hidden_questions))
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
        .options(joinedload(Item.posted_by), joinedload(Item.hidden_questions))
        .filter(Item.id == item.id)
        .one()
    )
    return _build_owner_response(item, db)


# ═══════════════════════════════════════════════════════════════════════════
# Feature D — Found Item Reporting
# Found items: no private description, no hidden questions, image mandatory,
# initial status FOUND, active 21 days (Section 7, Section 21.2).
# +2 trust points wired in Feature E (TrustService not yet built).
# ═══════════════════════════════════════════════════════════════════════════

_FOUND_ITEM_ACTIVE_DAYS = 21


def _build_found_response(item: Item) -> LostItemPublicResponse:
    """Found items have no owner-only fields — public response is the owner response."""
    return _build_public_response(item)


def create_found_item(
    db: Session,
    current_user: User,
    payload: CreateFoundItemRequest,
) -> LostItemPublicResponse:
    # Per-user daily rate limit: max 10 posts / day (Section 30.5)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_count = (
        db.query(Item)
        .filter(Item.posted_by_id == current_user.id, Item.created_at >= today_start)
        .count()
    )
    if daily_count >= 10:
        raise ValueError("You have reached the daily limit of 10 item posts")

    label, lat, lng, zone_id = _resolve_location(db, payload.location_id, current_user.university_id)

    _assert_not_duplicate_item_post(
        db,
        user_id=current_user.id,
        item_type=ItemType.FOUND,
        category=payload.category,
        public_description=payload.public_description,
        zone_id=zone_id,
    )

    expiry = datetime.now(timezone.utc) + timedelta(days=_FOUND_ITEM_ACTIVE_DAYS)

    item = Item(
        university_id=current_user.university_id,
        posted_by_id=current_user.id,
        item_type=ItemType.FOUND,
        status=ItemStatus.FOUND,
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
    db.add(item)
    db.flush()

    for idx, q in enumerate(payload.hidden_questions, start=1):
        db.add(
            ItemHiddenQuestion(
                item_id=item.id,
                question=encrypt(q.question),
                answer=encrypt(q.answer),
                position=idx,
            )
        )

    db.commit()

    item = (
        db.query(Item)
        .options(joinedload(Item.posted_by))
        .filter(Item.id == item.id)
        .one()
    )
    # +2 trust for posting a found item (Section 17.1 / Feature E)
    trust_service.award_found_item_posted(db, current_user.id, item.id)
    db.commit()
    return _build_found_response(item)


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
            Item.path_b_bridge == False,
            Item.path_c_bridge == False,
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

    if item.status not in (ItemStatus.FOUND, ItemStatus.POTENTIAL_MATCH):
        raise ValueError("Only active found items can be edited")

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
        .options(joinedload(Item.posted_by), joinedload(Item.hidden_questions))
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
        .options(joinedload(Item.posted_by), joinedload(Item.hidden_questions))
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
        .options(joinedload(Item.posted_by), joinedload(Item.hidden_questions))
        .filter(Item.id == item.id)
        .one()
    )
    return _build_found_response(item)


# ── Public Browse (Feature F) ─────────────────────────────────────────────────

# Statuses visible on the public feed (excludes returned/archived/closed/expired)
_VISIBLE_STATUSES = [
    ItemStatus.OPEN,
    ItemStatus.FOUND,
    ItemStatus.POTENTIAL_MATCH,
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
        Item.path_b_bridge == False,
        Item.path_c_bridge == False,
        Item.hidden_by_suspension == False,
        User.status == AccountStatus.ACTIVE,
    )


def _build_browse_card(
    item: Item,
    viewer_matched_ids: Optional[set] = None,
    path_b_viewer: Optional[tuple[str | None, uuid.UUID | None]] = None,
    path_c_viewer: Optional[tuple[str | None, uuid.UUID | None]] = None,
    chat_unlocked_ids: Optional[set] = None,
) -> BrowseItemCard:
    poster = BrowseItemPoster(
        id=item.posted_by.id,
        username=item.posted_by.username,
        display_name=item.posted_by.full_name or item.posted_by.username,
        trust_tier=trust_service.get_trust_tier(item.posted_by.trust_score),
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
    ):
        public_status = (
            ItemStatus.OPEN if item.item_type == ItemType.LOST else ItemStatus.FOUND
        )
    else:
        public_status = item.status
    pb_status, pb_conv = path_b_viewer if path_b_viewer else (None, None)
    pc_status, pc_conv = path_c_viewer if path_c_viewer else (None, None)
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
        viewer_path_b_status=pb_status if item.item_type == ItemType.LOST else None,
        viewer_path_b_conversation_id=pb_conv if item.item_type == ItemType.LOST else None,
        viewer_path_c_status=pc_status if item.item_type == ItemType.FOUND else None,
        viewer_path_c_conversation_id=pc_conv if item.item_type == ItemType.FOUND else None,
        viewer_chat_unlocked=bool(chat_unlocked_ids and item.id in chat_unlocked_ids),
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
    viewer_id: Optional[uuid.UUID] = None,
    chat_unlocked_ids: Optional[set] = None,
) -> BrowseListResponse:
    """
    Public browse feed — no auth required.
    Suspended users' items are excluded (Section 4.7).
    """
    query = (
        db.query(Item)
        .join(Item.posted_by)
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

    path_b_map: dict[uuid.UUID, tuple[str | None, uuid.UUID | None]] = {}
    path_c_map: dict[uuid.UUID, tuple[str | None, uuid.UUID | None]] = {}
    if viewer_id:
        lost_ids = [i.id for i in items if i.item_type == ItemType.LOST and i.posted_by_id != viewer_id]
        found_ids = [i.id for i in items if i.item_type == ItemType.FOUND and i.posted_by_id != viewer_id]
        path_b_map = path_b_service.resolve_viewer_path_b_statuses_batch(db, viewer_id, lost_ids)
        path_c_map = path_c_service.resolve_viewer_path_c_statuses_batch(db, viewer_id, found_ids)

    return BrowseListResponse(
        items=[
            _build_browse_card(
                i,
                viewer_matched_ids,
                path_b_map.get(i.id),
                path_c_map.get(i.id),
                chat_unlocked_ids,
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
    viewer_id: Optional[uuid.UUID] = None,
) -> HomepageResponse:
    """
    Lightweight homepage snapshot — 5 latest lost, 5 latest found,
    anonymous resolved items from past 7 days (Section 24.1).
    """
    def _active_query(type_filter: ItemType):
        return (
            db.query(Item)
            .join(Item.posted_by)
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

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    returned_filter = (
        ItemReturn.returned_at.isnot(None),
        ItemReturn.returned_at >= seven_days_ago,
        Item.status == ItemStatus.RETURNED,
    )
    recently_returned_count = (
        db.query(ItemReturn)
        .join(Item, Item.id == ItemReturn.lost_item_id)
        .filter(*returned_filter)
        .count()
    )

    path_b_map: dict[uuid.UUID, tuple[str | None, uuid.UUID | None]] = {}
    path_c_map: dict[uuid.UUID, tuple[str | None, uuid.UUID | None]] = {}
    chat_unlocked_ids: set[uuid.UUID] = set()
    if viewer_id:
        from app.services.matching_service import get_chat_unlocked_item_ids

        lost_ids = [i.id for i in latest_lost if i.posted_by_id != viewer_id]
        found_ids = [i.id for i in latest_found if i.posted_by_id != viewer_id]
        path_b_map = path_b_service.resolve_viewer_path_b_statuses_batch(
            db, viewer_id, lost_ids
        )
        path_c_map = path_c_service.resolve_viewer_path_c_statuses_batch(
            db, viewer_id, found_ids
        )
        chat_unlocked_ids = get_chat_unlocked_item_ids(db, viewer_id)

    return HomepageResponse(
        latest_lost=[
            _build_browse_card(
                i, viewer_matched_ids, path_b_map.get(i.id), None, chat_unlocked_ids,
            )
            for i in latest_lost
        ],
        latest_found=[
            _build_browse_card(
                i, viewer_matched_ids, None, path_c_map.get(i.id), chat_unlocked_ids,
            )
            for i in latest_found
        ],
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
        .join(Item, Item.id == ItemReturn.lost_item_id)
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
            id=item.id,
            category=item.category,
            item_name=_public_returned_item_name(item),
            returned_at=record.returned_at,
            university_short_name=university.short_name,
            finder_tipped=record.appreciation_sent_at is not None,
        )
        for record, item, university in rows
    ]
    return PublicReturnedListResponse(items=items, total=total)
