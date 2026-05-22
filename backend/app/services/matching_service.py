"""
AI Matching Engine — Section 10.

Runs after every lost/found item post (via FastAPI BackgroundTask).
Compares the new item against all active opposing items in the same university.

Score formula (Section 10.1):
  Description 0.40 | Image 0.15 | Location 0.15 | Date 0.15 | Category 0.15
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
from sqlalchemy.orm import Session, joinedload

from app.models.item import Item, ItemType, ItemStatus
from app.models.user import User, AccountStatus
from app.models.potential_match import PotentialMatch, PotentialMatchStatus
from app.services import notification_service

logger = logging.getLogger(__name__)

MATCH_THRESHOLD = 0.60

# Base weights (Section 10.1)
_W_DESC = 0.40
_W_IMG = 0.15
_W_LOC = 0.15
_W_DATE = 0.15
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


# ── Combined score (Section 10.1) ─────────────────────────────────────────────

def compute_match_score(item_a: Item, item_b: Item) -> tuple[float, dict]:
    """
    Returns (total_score, breakdown_dict).
    Public descriptions only — private descriptions never used (Section 10.2).
    """
    desc = description_similarity(item_a.public_description, item_b.public_description)

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
        logger.warning("run_matching_for_item: item %s not found", item_id)
        return []

    if source.status not in _POOL_STATUSES:
        return []

    candidates = _get_opposing_candidates(db, source)
    logger.info(
        "\n╔══════════════════════════════════════════════════════════════╗"
        "\n║  AI MATCHING ENGINE — new %s item posted"
        "\n║  Item ID  : %s"
        "\n║  Category : %s"
        "\n║  Location : %s"
        "\n║  Date     : %s"
        "\n║  Candidates found: %d"
        "\n╚══════════════════════════════════════════════════════════════╝",
        source.item_type.value.upper(),
        source.id,
        source.category.value,
        source.location_label or "unknown",
        source.date_occurred.strftime("%Y-%m-%d") if source.date_occurred else "unknown",
        len(candidates),
    )

    created: list[PotentialMatch] = []

    for candidate in candidates:
        if source.item_type == ItemType.LOST:
            lost_item, found_item = source, candidate
        else:
            lost_item, found_item = candidate, source

        if _existing_match(db, lost_item.id, found_item.id):
            logger.info(
                "[Matching] SKIP  lost=%-36s ↔ found=%-36s  reason=already_matched",
                lost_item.id, found_item.id,
            )
            continue

        score, breakdown = compute_match_score(lost_item, found_item)
        w = breakdown.get("weights", {})
        matched = score >= MATCH_THRESHOLD

        logger.info(
            "\n┌─ Comparing ──────────────────────────────────────────────────"
            "\n│  Lost  : %s  [%s]  \"%s\""
            "\n│  Found : %s  [%s]  \"%s\""
            "\n├─ Score Breakdown ────────────────────────────────────────────"
            "\n│  Description  : %.4f  (weight %.2f)"
            "\n│  Image        : %.4f  (weight %.2f)"
            "\n│  Location     : %.4f  (weight %.2f)"
            "\n│  Date         : %.4f  (weight %.2f)"
            "\n│  Category     : %.4f  (weight %.2f)"
            "\n├─ Result ─────────────────────────────────────────────────────"
            "\n│  Overall score : %.4f  (threshold %.2f)"
            "\n│  Decision      : %s"
            "\n└──────────────────────────────────────────────────────────────",
            lost_item.id,  lost_item.category.value,
            (lost_item.public_description or "")[:60].replace("\n", " "),
            found_item.id, found_item.category.value,
            (found_item.public_description or "")[:60].replace("\n", " "),
            breakdown.get("description", 0), w.get("description", 0),
            breakdown.get("image",       0), w.get("image",       0),
            breakdown.get("location",    0), w.get("location",    0),
            breakdown.get("date",        0), w.get("date",        0),
            breakdown.get("category",    0), w.get("category",    0),
            score, MATCH_THRESHOLD,
            "✅ PotentialMatch CREATED" if matched else f"❌ Below threshold — skipped",
        )

        if not matched:
            continue

        match = _create_potential_match(db, lost_item, found_item, score, breakdown)
        created.append(match)

    if created:
        db.commit()
        logger.info(
            "[Matching] ✅ Done — %d PotentialMatch record(s) saved for item %s",
            len(created), source.id,
        )
    else:
        logger.info(
            "[Matching] ✅ Done — no matches above threshold for item %s",
            source.id,
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

def get_matched_item_ids(db: Session, user_id: uuid.UUID) -> set[uuid.UUID]:
    """
    Return ALL item IDs (own + opposing) that are part of an active/paused
    match involving this user. Used by browse/homepage feeds so the viewer
    can see the real POTENTIAL_MATCH status on both their own item and the
    opposing item they are matched with.
    """
    my_item_ids = [
        row[0] for row in db.query(Item.id).filter(Item.posted_by_id == user_id).all()
    ]
    if not my_item_ids:
        return set()

    matches = (
        db.query(PotentialMatch.lost_item_id, PotentialMatch.found_item_id)
        .filter(
            PotentialMatch.status.in_([
                PotentialMatchStatus.ACTIVE,
                PotentialMatchStatus.PAUSED,
            ]),
            or_(
                PotentialMatch.lost_item_id.in_(my_item_ids),
                PotentialMatch.found_item_id.in_(my_item_ids),
            ),
        )
        .all()
    )
    result: set[uuid.UUID] = set()
    for lost_id, found_id in matches:
        result.add(lost_id)
        result.add(found_id)
    return result


def list_matches_for_user(db: Session, user_id: uuid.UUID) -> list[PotentialMatch]:
    """All active/paused matches where the user owns the lost or found item."""
    my_item_ids = [
        row[0] for row in db.query(Item.id).filter(Item.posted_by_id == user_id).all()
    ]
    if not my_item_ids:
        return []

    return (
        db.query(PotentialMatch)
        .options(
            joinedload(PotentialMatch.lost_item).joinedload(Item.posted_by),
            joinedload(PotentialMatch.found_item).joinedload(Item.posted_by),
        )
        .filter(
            PotentialMatch.status.in_([
                PotentialMatchStatus.ACTIVE,
                PotentialMatchStatus.PAUSED,
            ]),
            or_(
                PotentialMatch.lost_item_id.in_(my_item_ids),
                PotentialMatch.found_item_id.in_(my_item_ids),
            ),
        )
        .order_by(PotentialMatch.match_score.desc())
        .all()
    )
