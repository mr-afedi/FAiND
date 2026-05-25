"""
Item service — business logic for Lost & Found Item Reporting (Features C & D).
Business logic lives here; route handlers only handle request/response.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.models.item import Item, ItemHiddenQuestion, ItemStatus, ItemType
from app.models.campus_zone import CampusZone
from app.models.user import User, AccountStatus
from app.models.potential_match import PotentialMatch, PotentialMatchStatus
import app.services.trust_service as trust_service
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
    BrowseItemPoster,
    BrowseItemCard,
    BrowseListResponse,
    RecentlyReturnedItem,
    HomepageResponse,
)
from app.utils.encryption import encrypt

# Lost items are active for 45 days (Section 21.1)
_LOST_ITEM_ACTIVE_DAYS = 45


# ── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_location(
    db: Session, location_id: Optional[uuid.UUID], university_id: uuid.UUID
) -> tuple[str, Optional[float], Optional[float], Optional[uuid.UUID]]:
    """Return (label, lat, lng, zone_id) for the chosen zone, or raise ValueError."""
    if location_id is None:
        return ("Unknown Location", None, None, None)

    zone: Optional[CampusZone] = (
        db.query(CampusZone)
        .filter(CampusZone.id == location_id, CampusZone.university_id == university_id, CampusZone.is_active == True)
        .first()
    )
    if not zone:
        raise ValueError("Campus zone not found or does not belong to your university")
    return (zone.name, zone.latitude, zone.longitude, zone.id)


def _build_owner_response(
    item: Item,
    db: Session,
    override_status: Optional[ItemStatus] = None,
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
    )


def _build_public_response(
    item: Item,
    mask_match_status: bool = False,
    show_as_matched: bool = False,
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
    ):
        visible_status = (
            ItemStatus.OPEN if item.item_type == ItemType.LOST else ItemStatus.FOUND
        )
    elif item.status == ItemStatus.UNDER_VERIFICATION:
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
    )


# ── Create ───────────────────────────────────────────────────────────────────

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

    expiry = datetime.now(timezone.utc) + timedelta(days=_LOST_ITEM_ACTIVE_DAYS)

    item = Item(
        university_id=current_user.university_id,
        posted_by_id=current_user.id,
        item_type=ItemType.LOST,
        status=ItemStatus.OPEN,
        category=payload.category,
        public_description=payload.public_description,
        private_description=encrypt(payload.private_description),
        location_id=zone_id,
        location_label=label,
        location_lat=lat,
        location_lng=lng,
        date_occurred=payload.date_occurred,
        image_urls=payload.image_urls,
        expiry_date=expiry,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

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
        # Found items stay "found" in the DB even when matched — show the real
        # match status to the owner so they know a match exists.
        override = (
            ItemStatus.POTENTIAL_MATCH
            if active_match and current_user.id in party_ids
            else None
        )
        return _build_owner_response(item, db, override_status=override)

    # Non-owner: party members always see POTENTIAL_MATCH badge (even on found items
    # whose DB status is "found"). Everyone else gets the masked status.
    is_party = current_user is not None and current_user.id in party_ids
    return _build_public_response(
        item,
        show_as_matched=is_party and active_match is not None,
        mask_match_status=not is_party,
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
    expiry = datetime.now(timezone.utc) + timedelta(days=_FOUND_ITEM_ACTIVE_DAYS)

    item = Item(
        university_id=current_user.university_id,
        posted_by_id=current_user.id,
        item_type=ItemType.FOUND,
        status=ItemStatus.FOUND,
        category=payload.category,
        public_description=payload.public_description,
        private_description=None,
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
    db.commit()

    item = (
        db.query(Item)
        .options(joinedload(Item.posted_by), joinedload(Item.hidden_questions))
        .filter(Item.id == item.id)
        .one()
    )
    return _build_found_response(item)


# ── Public Browse (Feature F) ─────────────────────────────────────────────────

# Statuses visible on the public feed (excludes archived/closed/expired)
_VISIBLE_STATUSES = [
    ItemStatus.OPEN,
    ItemStatus.FOUND,
    ItemStatus.POTENTIAL_MATCH,
    ItemStatus.UNDER_VERIFICATION,
    ItemStatus.UNDER_DISPUTE,
]


def _build_browse_card(
    item: Item,
    viewer_matched_ids: Optional[set] = None,
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
    is_party = bool(viewer_matched_ids and item.id in viewer_matched_ids)
    if is_party:
        public_status = ItemStatus.POTENTIAL_MATCH
    elif item.status in (ItemStatus.POTENTIAL_MATCH, ItemStatus.UNDER_VERIFICATION):
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
) -> BrowseListResponse:
    """
    Public browse feed — no auth required.
    Suspended users' items are excluded (Section 4.7).
    """
    query = (
        db.query(Item)
        .join(Item.posted_by)
        .options(joinedload(Item.posted_by))
        .filter(
            Item.status.in_(_VISIBLE_STATUSES),
            User.status == AccountStatus.ACTIVE,
        )
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
    return BrowseListResponse(
        items=[_build_browse_card(i, viewer_matched_ids) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


def get_homepage_data(db: Session, viewer_matched_ids: Optional[set] = None) -> HomepageResponse:
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
                Item.status.in_(_VISIBLE_STATUSES),
                User.status == AccountStatus.ACTIVE,
            )
            .order_by(Item.created_at.desc())
            .limit(5)
            .all()
        )

    latest_lost = _active_query(ItemType.LOST)
    latest_found = _active_query(ItemType.FOUND)

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    returned_rows = (
        db.query(Item)
        .filter(
            Item.status == ItemStatus.RETURNED,
            Item.updated_at >= seven_days_ago,
        )
        .order_by(Item.updated_at.desc())
        .limit(10)
        .all()
    )

    recently_returned = [
        RecentlyReturnedItem(id=i.id, category=i.category, returned_at=i.updated_at)
        for i in returned_rows
    ]

    return HomepageResponse(
        latest_lost=[_build_browse_card(i, viewer_matched_ids) for i in latest_lost],
        latest_found=[_build_browse_card(i, viewer_matched_ids) for i in latest_found],
        recently_returned=recently_returned,
    )
