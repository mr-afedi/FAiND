"""
AI Matching Engine — Section 10.

Runs after every lost/found item post (via FastAPI BackgroundTask).
Compares the new item against all active opposing items in the same university.

Score formula (Section 10.1):
  Description 0.45 | Image 0.15 | Location 0.125 | Date 0.125 | Category 0.15
  Image weight redistributes when either item has no image.

Threshold: >= 0.60 → PotentialMatch + notify both users; lost item → POTENTIAL_MATCH.
"""
from __future__ import annotations

import io
import logging
import re
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

import httpx
import numpy as np
from geopy.distance import geodesic
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, aliased

from app.models.item import Item, ItemCategory, ItemType, ItemStatus
from app.models.user import User, AccountStatus
from app.models.potential_match import PotentialMatch, PotentialMatchStatus
from app.models.conversation import Conversation, ConversationStatus
from app.models.verification_attempt import VerificationAttempt, VerificationResult
from app.services import notification_service

logger = logging.getLogger(__name__)

MATCH_THRESHOLD = 0.60
_MIN_DESCRIPTION_SIMILARITY = 0.35

# Base weights (Section 10.1)
_W_DESC = 0.45
_W_IMG = 0.15
_W_LOC = 0.125
_W_DATE = 0.125
_W_CAT = 0.15

# Items eligible in the matching pool (Section 10.8)
_POOL_STATUSES = [
    ItemStatus.OPEN,
    ItemStatus.FOUND,
    ItemStatus.POTENTIAL_MATCH,
]

# Opposing statuses when searching candidates (Section 10.8)
# When the new item is FOUND, we search for LOST items (OPEN or POTENTIAL_MATCH)
# When the new item is LOST, we search for FOUND items (FOUND or POTENTIAL_MATCH)
_LOST_CANDIDATES_POOL = [ItemStatus.OPEN, ItemStatus.POTENTIAL_MATCH]
_FOUND_CANDIDATES_POOL = [ItemStatus.FOUND, ItemStatus.POTENTIAL_MATCH]


# ── ML model (lazy singleton) ───────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_sentence_model():
    """Load all-MiniLM-L6-v2 once (~80MB). Returns None if not installed."""
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as exc:
        logger.warning("sentence-transformers unavailable: %s — using text fallback", exc)
        return None


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _embed_texts(texts: list[str]) -> list[np.ndarray]:
    model = _get_sentence_model()
    if model is not None:
        vecs = model.encode(texts, normalize_embeddings=True)
        return [np.array(v, dtype=np.float32) for v in vecs]
    # Token-overlap fallback when sentence-transformers is not installed
    return [_token_vector(t) for t in texts]


def _token_vector(text: str) -> np.ndarray:
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    if not tokens:
        return np.zeros(128, dtype=np.float32)
    vec = np.zeros(128, dtype=np.float32)
    for tok in tokens:
        vec[hash(tok) % 128] += 1.0
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def description_similarity(text_a: str, text_b: str) -> float:
    """Section 10.2 — public descriptions only."""
    if not text_a.strip() or not text_b.strip():
        return 0.0
    vecs = _embed_texts([text_a.strip(), text_b.strip()])
    return max(0.0, min(1.0, _cosine_similarity(vecs[0], vecs[1])))


# ── Image similarity (Section 10.3) ───────────────────────────────────────────

def _fetch_image_bytes(url: str) -> Optional[bytes]:
    try:
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return resp.content
    except Exception as exc:
        logger.debug("Image fetch failed for %s: %s", url, exc)
    return None


def image_similarity(url_a: Optional[str], url_b: Optional[str]) -> float:
    """phash Hamming distance normalised to 0.0–1.0."""
    if not url_a or not url_b:
        return 0.0
    try:
        import imagehash
        from PIL import Image

        bytes_a = _fetch_image_bytes(url_a)
        bytes_b = _fetch_image_bytes(url_b)
        if not bytes_a or not bytes_b:
            return 0.0

        hash_a = imagehash.phash(Image.open(io.BytesIO(bytes_a)))
        hash_b = imagehash.phash(Image.open(io.BytesIO(bytes_b)))
        distance = hash_a - hash_b  # Hamming distance, max 64 for phash
        return max(0.0, 1.0 - (distance / 64.0))
    except Exception as exc:
        logger.debug("Image similarity error: %s", exc)
        return 0.0


# ── Location proximity (Section 10.4) ─────────────────────────────────────────

def location_proximity_score(
    lat_a: Optional[float], lng_a: Optional[float],
    lat_b: Optional[float], lng_b: Optional[float],
) -> float:
    if lat_a is None or lng_a is None or lat_b is None or lng_b is None:
        return 0.0
    try:
        metres = geodesic((lat_a, lng_a), (lat_b, lng_b)).meters
    except Exception:
        return 0.0

    if metres <= 100:
        return 1.0
    if metres <= 300:
        return 0.75
    if metres <= 600:
        return 0.50
    if metres <= 1000:
        return 0.25
    return 0.0


# ── Date proximity (Section 10.5) ─────────────────────────────────────────────

def date_proximity_score(date_a: datetime, date_b: datetime) -> float:
    days = abs((date_a - date_b).total_seconds()) / 86400.0
    if days <= 1:
        return 1.0
    if days <= 3:
        return 0.75
    if days <= 7:
        return 0.50
    if days <= 14:
        return 0.25
    return 0.0


# ── Category match (Section 10.6) ───────────────────────────────────────────────

def category_match_score(cat_a, cat_b) -> float:
    return 1.0 if cat_a == cat_b else 0.0


def _is_category_hard_blocked(cat_a: ItemCategory, cat_b: ItemCategory) -> bool:
    """
    Different categories disqualify the pair unless either item is Other.
    """
    if cat_a == cat_b:
        return False
    if cat_a == ItemCategory.OTHER or cat_b == ItemCategory.OTHER:
        return False
    return True


def _disqualified_breakdown(reason: str, **fields: float) -> dict:
    """Score breakdown for pairs that fail pre-threshold gates."""
    breakdown = {
        "description": 0.0,
        "image": 0.0,
        "location": 0.0,
        "date": 0.0,
        "category": 0.0,
        "total": 0.0,
        "weights": {
            "description": _W_DESC,
            "image": _W_IMG,
            "location": _W_LOC,
            "date": _W_DATE,
            "category": _W_CAT,
        },
        "disqualified": reason,
    }
    for key, value in fields.items():
        breakdown[key] = value
    return breakdown


# ── Combined score (Section 10.1) ─────────────────────────────────────────────

def compute_match_score(item_a: Item, item_b: Item) -> tuple[float, dict]:
    """
    Returns (total_score, breakdown_dict).
    Public descriptions only — private descriptions never used (Section 10.2).
    """
    if _is_category_hard_blocked(item_a.category, item_b.category):
        return 0.0, _disqualified_breakdown("category_mismatch", category=0.0)

    desc = description_similarity(item_a.public_description, item_b.public_description)
    if desc < _MIN_DESCRIPTION_SIMILARITY:
        return 0.0, _disqualified_breakdown(
            "description_below_minimum",
            description=round(float(desc), 4),
        )

    has_img_a = bool(item_a.image_urls)
    has_img_b = bool(item_b.image_urls)
    if has_img_a and has_img_b:
        img = image_similarity(item_a.image_urls[0], item_b.image_urls[0])
        w_desc, w_img, w_loc, w_date, w_cat = _W_DESC, _W_IMG, _W_LOC, _W_DATE, _W_CAT
    else:
        img = 0.0
        # Redistribute image weight proportionally across remaining factors
        remaining = _W_DESC + _W_LOC + _W_DATE + _W_CAT
        factor = 1.0 / remaining
        w_desc = _W_DESC * factor
        w_img = 0.0
        w_loc = _W_LOC * factor
        w_date = _W_DATE * factor
        w_cat = _W_CAT * factor

    loc = location_proximity_score(
        item_a.location_lat, item_a.location_lng,
        item_b.location_lat, item_b.location_lng,
    )
    date = date_proximity_score(item_a.date_occurred, item_b.date_occurred)
    cat = category_match_score(item_a.category, item_b.category)

    # False positive guard: perfect location + date but description below 0.60
    # (typical pattern: desc < 0.55 with loc/date 1.0 — different items, same place/day)
    if loc == 1.0 and date == 1.0 and desc < 0.60:
        return 0.0, _disqualified_breakdown(
            "description_too_weak_for_perfect_location_date",
            description=round(float(desc), 4),
            location=round(float(loc), 4),
            date=round(float(date), 4),
        )

    total = w_desc * desc + w_img * img + w_loc * loc + w_date * date + w_cat * cat
    total = max(0.0, min(1.0, float(total)))

    breakdown = {
        "description": round(float(desc), 4),
        "image": round(float(img), 4),
        "location": round(float(loc), 4),
        "date": round(float(date), 4),
        "category": round(float(cat), 4),
        "total": round(total, 4),
        "weights": {
            "description": round(float(w_desc), 4),
            "image": round(float(w_img), 4),
            "location": round(float(w_loc), 4),
            "date": round(float(w_date), 4),
            "category": round(float(w_cat), 4),
        },
    }
    return total, breakdown


# ── Matching orchestration ────────────────────────────────────────────────────

def _get_opposing_candidates(db: Session, source: Item) -> list[Item]:
    """Return active opposing-type items in the same university (Section 10.8)."""
    if source.item_type == ItemType.LOST:
        opposing_type = ItemType.FOUND
        statuses = _FOUND_CANDIDATES_POOL
    else:
        opposing_type = ItemType.LOST
        statuses = _LOST_CANDIDATES_POOL

    return (
        db.query(Item)
        .join(Item.posted_by)
        .options(joinedload(Item.posted_by))
        .filter(
            Item.university_id == source.university_id,
            Item.item_type == opposing_type,
            Item.status.in_(statuses),
            Item.id != source.id,
            Item.posted_by_id != source.posted_by_id,
            User.status == AccountStatus.ACTIVE,
        )
        .all()
    )


def _existing_match(db: Session, lost_id: uuid.UUID, found_id: uuid.UUID) -> bool:
    return (
        db.query(PotentialMatch)
        .filter(
            PotentialMatch.lost_item_id == lost_id,
            PotentialMatch.found_item_id == found_id,
        )
        .first()
        is not None
    )


def _create_potential_match(
    db: Session,
    lost_item: Item,
    found_item: Item,
    score: float,
    breakdown: dict,
) -> PotentialMatch:
    match = PotentialMatch(
        university_id=lost_item.university_id,
        lost_item_id=lost_item.id,
        found_item_id=found_item.id,
        match_score=float(round(score, 4)),
        score_breakdown=breakdown,
        status=PotentialMatchStatus.ACTIVE,
    )
    db.add(match)

    # Path A step 4: lost item status → POTENTIAL_MATCH
    if lost_item.status == ItemStatus.OPEN:
        lost_item.status = ItemStatus.POTENTIAL_MATCH

    db.flush()

    pct = int(score * 100)
    notification_service.notify_match_found(
        db,
        lost_owner_id=lost_item.posted_by_id,
        found_owner_id=found_item.posted_by_id,
        match_id=match.id,
        lost_item_id=lost_item.id,
        found_item_id=found_item.id,
        score_pct=pct,
    )
    return match


def run_matching_for_item(db: Session, item_id: uuid.UUID) -> list[PotentialMatch]:
    """
    Compare one newly posted item against the opposing pool.
    Called from BackgroundTask after item creation commits.
    """
    source: Optional[Item] = (
        db.query(Item)
        .options(joinedload(Item.posted_by))
        .filter(Item.id == item_id)
        .first()
    )
    if not source:
        print(f"[Matching] WARNING: item {item_id} not found in DB", flush=True)
        return []

    if source.status not in _POOL_STATUSES:
        return []

    candidates = _get_opposing_candidates(db, source)
    print(
        f"\n╔══════════════════════════════════════════════════════════════╗"
        f"\n║  AI MATCHING ENGINE — new {source.item_type.value.upper()} item posted"
        f"\n║  Item ID  : {source.id}"
        f"\n║  Category : {source.category.value}"
        f"\n║  Location : {source.location_label or 'unknown'}"
        f"\n║  Date     : {source.date_occurred.strftime('%Y-%m-%d') if source.date_occurred else 'unknown'}"
        f"\n║  Candidates found: {len(candidates)}"
        f"\n╚══════════════════════════════════════════════════════════════╝",
        flush=True,
    )

    created: list[PotentialMatch] = []

    for candidate in candidates:
        if source.item_type == ItemType.LOST:
            lost_item, found_item = source, candidate
        else:
            lost_item, found_item = candidate, source

        if _existing_match(db, lost_item.id, found_item.id):
            print(
                f"[Matching] SKIP  lost={lost_item.id} ↔ found={found_item.id}  reason=already_matched",
                flush=True,
            )
            continue

        score, breakdown = compute_match_score(lost_item, found_item)
        w = breakdown.get("weights", {})
        disqualified = breakdown.get("disqualified")
        matched = not disqualified and score >= MATCH_THRESHOLD

        if disqualified:
            decision = f"❌ Disqualified — {disqualified}"
        elif matched:
            decision = "✅ PotentialMatch CREATED"
        else:
            decision = "❌ Below threshold — skipped"
        print(
            f"\n┌─ Comparing ──────────────────────────────────────────────────"
            f"\n│  Lost  : {lost_item.id}  [{lost_item.category.value}]"
            f"\n│          \"{(lost_item.public_description or '')[:60].replace(chr(10), ' ')}\""
            f"\n│  Found : {found_item.id}  [{found_item.category.value}]"
            f"\n│          \"{(found_item.public_description or '')[:60].replace(chr(10), ' ')}\""
            f"\n├─ Score Breakdown ────────────────────────────────────────────"
            f"\n│  Description  : {breakdown.get('description', 0):.4f}  (weight {w.get('description', 0):.2f})"
            f"\n│  Image        : {breakdown.get('image', 0):.4f}  (weight {w.get('image', 0):.2f})"
            f"\n│  Location     : {breakdown.get('location', 0):.4f}  (weight {w.get('location', 0):.2f})"
            f"\n│  Date         : {breakdown.get('date', 0):.4f}  (weight {w.get('date', 0):.2f})"
            f"\n│  Category     : {breakdown.get('category', 0):.4f}  (weight {w.get('category', 0):.2f})"
            f"\n├─ Result ─────────────────────────────────────────────────────"
            f"\n│  Overall score : {score:.4f}  (threshold {MATCH_THRESHOLD:.2f})"
            f"\n│  Decision      : {decision}"
            f"\n└──────────────────────────────────────────────────────────────",
            flush=True,
        )

        if not matched:
            continue

        match = _create_potential_match(db, lost_item, found_item, score, breakdown)
        created.append(match)

    if created:
        db.commit()
        print(
            f"\n[Matching] ✅ Done — {len(created)} PotentialMatch record(s) saved for item {source.id}\n",
            flush=True,
        )
    else:
        print(
            f"\n[Matching] ✅ Done — no matches above threshold for item {source.id}\n",
            flush=True,
        )
    return created


def run_matching_background(item_id: uuid.UUID) -> None:
    """Entry point for FastAPI BackgroundTasks — opens its own DB session."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        run_matching_for_item(db, item_id)
    except Exception:
        logger.exception("Background matching failed for item %s", item_id)
        db.rollback()
    finally:
        db.close()


# Match statuses cancelled when an item is archived (Section 21.5)
_LIVE_MATCH_STATUSES = [
    PotentialMatchStatus.ACTIVE,
    PotentialMatchStatus.PENDING_REVIEW,
    PotentialMatchStatus.PAUSED,
    PotentialMatchStatus.VERIFIED,
]

_REVERTABLE_ITEM_STATUSES = (
    ItemStatus.POTENTIAL_MATCH,
    ItemStatus.UNDER_VERIFICATION,
)


def _revert_item_to_active_pool(item: Item) -> None:
    """Restore the surviving item to the public feed after its pair is archived."""
    if item.status not in _REVERTABLE_ITEM_STATUSES:
        return
    item.status = (
        ItemStatus.OPEN if item.item_type == ItemType.LOST else ItemStatus.FOUND
    )


def _expire_matches_for_archived_item(db: Session, item_id: uuid.UUID) -> list[PotentialMatch]:
    """
    Expire all live PotentialMatch rows for this item and revert the surviving peer.
    Path B/C claims use PENDING_REVIEW matches until dedicated claim tables exist.
    Does not commit — caller must commit.
    """
    matches = (
        db.query(PotentialMatch)
        .options(
            joinedload(PotentialMatch.lost_item),
            joinedload(PotentialMatch.found_item),
        )
        .filter(
            PotentialMatch.status.in_(_LIVE_MATCH_STATUSES),
            or_(
                PotentialMatch.lost_item_id == item_id,
                PotentialMatch.found_item_id == item_id,
            ),
        )
        .all()
    )
    for match in matches:
        match.status = PotentialMatchStatus.EXPIRED
        for paired in (match.lost_item, match.found_item):
            if paired.id != item_id:
                _revert_item_to_active_pool(paired)

        conv = (
            db.query(Conversation)
            .filter(Conversation.potential_match_id == match.id)
            .first()
        )
        if conv and conv.status != ConversationStatus.FROZEN:
            conv.status = ConversationStatus.FROZEN

    return matches


def _cancel_active_verifications_for_item(db: Session, item_id: uuid.UUID) -> int:
    """
    Cancel in-flight verifications: admin-review (REVIEW) attempts for this item.
    Covers Path A/B/C — Path B/C enums exist; claim rows are not separate yet.
    Does not commit — caller must commit.
    """
    attempts = (
        db.query(VerificationAttempt)
        .filter(
            VerificationAttempt.result == VerificationResult.REVIEW,
            or_(
                VerificationAttempt.lost_item_id == item_id,
                VerificationAttempt.found_item_id == item_id,
            ),
        )
        .all()
    )
    for attempt in attempts:
        attempt.result = VerificationResult.REJECTED
    return len(attempts)


def cleanup_on_item_archive(db: Session, item_id: uuid.UUID) -> tuple[int, int]:
    """
    Full archive side-effects (Section 21.5): expire matches, cancel pending
    verifications, freeze chats. Single commit at end.
    """
    expired_matches = _expire_matches_for_archived_item(db, item_id)
    cancelled_attempts = _cancel_active_verifications_for_item(db, item_id)
    db.commit()
    logger.info(
        "cleanup_on_item_archive: item=%s expired_matches=%d cancelled_verifications=%d",
        item_id,
        len(expired_matches),
        cancelled_attempts,
    )
    return len(expired_matches), cancelled_attempts


def expire_matches_for_archived_item(db: Session, item_id: uuid.UUID) -> int:
    """Backward-compatible wrapper — prefer cleanup_on_item_archive from delete flows."""
    count, _ = cleanup_on_item_archive(db, item_id)
    return count


# ── Dispute helpers (Section 10.10) ──────────────────────────────────────────

def pause_matches_for_item(db: Session, item_id: uuid.UUID) -> int:
    """
    When an item enters UNDER_DISPUTE, pause ALL its active PotentialMatch records.
    Called by Feature I/R dispute handlers. Returns count of paused records.
    """
    matches = (
        db.query(PotentialMatch)
        .filter(
            PotentialMatch.status == PotentialMatchStatus.ACTIVE,
            or_(
                PotentialMatch.lost_item_id == item_id,
                PotentialMatch.found_item_id == item_id,
            ),
        )
        .all()
    )
    for m in matches:
        m.status = PotentialMatchStatus.PAUSED
    if matches:
        db.commit()
    logger.info("pause_matches_for_item: paused %d matches for item %s", len(matches), item_id)
    return len(matches)


def resume_matches_for_item(db: Session, item_id: uuid.UUID) -> int:
    """
    On dispute resolution, resume PAUSED matches for this item.
    Called by Feature R (admin dispute resolution). Returns count resumed.
    """
    matches = (
        db.query(PotentialMatch)
        .filter(
            PotentialMatch.status == PotentialMatchStatus.PAUSED,
            or_(
                PotentialMatch.lost_item_id == item_id,
                PotentialMatch.found_item_id == item_id,
            ),
        )
        .all()
    )
    for m in matches:
        m.status = PotentialMatchStatus.ACTIVE
    if matches:
        db.commit()
    logger.info("resume_matches_for_item: resumed %d matches for item %s", len(matches), item_id)
    return len(matches)


# ── Read helpers ──────────────────────────────────────────────────────────────

def _live_matches_for_user_query(db: Session, user_id: uuid.UUID):
    """PotentialMatches involving the user's items; excludes archived items."""
    my_item_ids = [
        row[0]
        for row in db.query(Item.id).filter(
            Item.posted_by_id == user_id,
            Item.status != ItemStatus.ARCHIVED,
        ).all()
    ]
    if not my_item_ids:
        return None

    LostItem = aliased(Item)
    FoundItem = aliased(Item)
    return (
        db.query(PotentialMatch)
        .options(
            joinedload(PotentialMatch.lost_item).joinedload(Item.posted_by),
            joinedload(PotentialMatch.found_item).joinedload(Item.posted_by),
        )
        .join(LostItem, PotentialMatch.lost_item_id == LostItem.id)
        .join(FoundItem, PotentialMatch.found_item_id == FoundItem.id)
        .filter(
            PotentialMatch.status.in_(_LIVE_MATCH_STATUSES),
            LostItem.status != ItemStatus.ARCHIVED,
            FoundItem.status != ItemStatus.ARCHIVED,
            or_(
                PotentialMatch.lost_item_id.in_(my_item_ids),
                PotentialMatch.found_item_id.in_(my_item_ids),
            ),
        )
    )


def get_matched_item_ids(db: Session, user_id: uuid.UUID) -> set[uuid.UUID]:
    """
    Return ALL item IDs (own + opposing) that are part of an active/paused
    match involving this user. Used by browse/homepage feeds so the viewer
    can see the real POTENTIAL_MATCH status on both their own item and the
    opposing item they are matched with.
    """
    q = _live_matches_for_user_query(db, user_id)
    if q is None:
        return set()

    result: set[uuid.UUID] = set()
    for match in q.all():
        result.add(match.lost_item_id)
        result.add(match.found_item_id)
    return result


def list_matches_for_user(db: Session, user_id: uuid.UUID) -> list[PotentialMatch]:
    """All live matches where the user owns the lost or found item (archived excluded)."""
    q = _live_matches_for_user_query(db, user_id)
    if q is None:
        return []

    return q.order_by(PotentialMatch.match_score.desc()).all()
