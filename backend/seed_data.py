"""
Seed the database with the GCTU university and campus zones defined in Section 9.2.
Safe to run multiple times — idempotent.

Usage: python seed_data.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.university import University
from app.models.campus_zone import CampusZone

# GCTU is located in Accra, Ghana (approx. 5.605°N, -0.187°E)
GCTU_ZONES = [
    {"name": "Main Library",           "latitude": 5.6062,  "longitude": -0.1860},
    {"name": "Block A Lecture Hall",   "latitude": 5.6055,  "longitude": -0.1872},
    {"name": "Block B Lecture Hall",   "latitude": 5.6050,  "longitude": -0.1868},
    {"name": "Cafeteria / Canteen",    "latitude": 5.6058,  "longitude": -0.1855},
    {"name": "Administration Block",   "latitude": 5.6065,  "longitude": -0.1875},
    {"name": "ICT Lab",                "latitude": 5.6052,  "longitude": -0.1862},
    {"name": "Student Services Centre","latitude": 5.6060,  "longitude": -0.1878},
    {"name": "Car Park",               "latitude": 5.6070,  "longitude": -0.1880},
    {"name": "Sports Ground",          "latitude": 5.6045,  "longitude": -0.1850},
    {"name": "Main Gate / Entrance",   "latitude": 5.6075,  "longitude": -0.1885},
]


def seed():
    db = SessionLocal()
    try:
        # University
        gctu = db.query(University).filter(University.short_name == "GCTU").first()
        if not gctu:
            gctu = University(
                name="Ghana Communication Technology University",
                short_name="GCTU",
                email_domain="live.gctu.edu.gh",
                description="Ghana's premier ICT-focused university.",
                is_active=True,
            )
            db.add(gctu)
            db.flush()
            print(f"[SEED] Created university: {gctu.name} (id={gctu.id})")
        else:
            print(f"[SEED] University already exists: {gctu.name}")

        # Campus zones
        existing_names = {
            z.name for z in db.query(CampusZone).filter(CampusZone.university_id == gctu.id).all()
        }

        added = 0
        for zone_data in GCTU_ZONES:
            if zone_data["name"] not in existing_names:
                zone = CampusZone(
                    university_id=gctu.id,
                    name=zone_data["name"],
                    latitude=zone_data["latitude"],
                    longitude=zone_data["longitude"],
                    is_active=True,
                )
                db.add(zone)
                added += 1

        db.commit()
        print(f"[SEED] Added {added} new campus zone(s). Total zones: {len(GCTU_ZONES)}.")
        print("[SEED] Done.")

    except Exception as e:
        db.rollback()
        print(f"[SEED ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
