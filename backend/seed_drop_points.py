"""
Seed the 7 GCTU drop points defined in Section 4.1.
Safe to run multiple times — idempotent.

Usage: python seed_drop_points.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.drop_point import DropPoint, DropPointType
from app.models.university import University

# Placeholder coordinates around GCTU campus — replace with real values later.
GCTU_DROP_POINTS = [
    {
        "name": "Faculty of Computing and Information Systems (FoCIS)",
        "type": DropPointType.FACULTY,
        "latitude": 5.6058,
        "longitude": -0.1865,
    },
    {
        "name": "Faculty of IT Business",
        "type": DropPointType.FACULTY,
        "latitude": 5.6053,
        "longitude": -0.1860,
    },
    {
        "name": "Faculty of Engineering",
        "type": DropPointType.FACULTY,
        "latitude": 5.6048,
        "longitude": -0.1870,
    },
    {
        "name": "School of Graduate Studies and Research",
        "type": DropPointType.FACULTY,
        "latitude": 5.6063,
        "longitude": -0.1878,
    },
    {
        "name": "Gate 1",
        "type": DropPointType.SECURITY,
        "latitude": 5.6075,
        "longitude": -0.1885,
    },
    {
        "name": "Gate 2",
        "type": DropPointType.SECURITY,
        "latitude": 5.6070,
        "longitude": -0.1875,
    },
    {
        "name": "Gate 3",
        "type": DropPointType.SECURITY,
        "latitude": 5.6065,
        "longitude": -0.1860,
    },
]


def seed():
    db = SessionLocal()
    try:
        gctu = db.query(University).filter(University.short_name == "GCTU").first()
        if not gctu:
            print("[SEED ERROR] GCTU university not found. Run seed_data.py first.")
            return

        existing_names = {
            dp.name
            for dp in db.query(DropPoint).filter(DropPoint.university_id == gctu.id).all()
        }

        added = 0
        for entry in GCTU_DROP_POINTS:
            if entry["name"] in existing_names:
                continue
            db.add(
                DropPoint(
                    university_id=gctu.id,
                    name=entry["name"],
                    type=entry["type"],
                    latitude=entry["latitude"],
                    longitude=entry["longitude"],
                    operating_hours="Mon-Fri 08:00-17:00",
                    is_temporarily_closed=False,
                    closed_reason=None,
                )
            )
            added += 1

        db.commit()
        total = db.query(DropPoint).filter(DropPoint.university_id == gctu.id).count()
        print(f"[SEED] Added {added} new drop point(s). Total GCTU drop points: {total}.")
        print("[SEED] Done.")
    except Exception as exc:
        db.rollback()
        print(f"[SEED ERROR] {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
