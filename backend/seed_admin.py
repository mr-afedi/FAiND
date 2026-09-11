"""
Seed the Root Admin account.
Reads credentials from environment variables:
  ROOT_ADMIN_EMAIL, ROOT_ADMIN_PASSWORD, ROOT_ADMIN_TOTP_SECRET

This script is idempotent — it will never create a second root admin.
DELETE OR DISABLE this script after the first successful run in production.

Usage: python seed_admin.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.core.config import get_settings
from app.models.user import User, UserRole, AccountStatus
from app.models.university import University
from app.utils.totp_utils import is_valid_totp_secret, normalize_totp_secret

settings = get_settings()


def seed_admin():
    if not settings.ROOT_ADMIN_EMAIL:
        print("[SEED ADMIN ERROR] ROOT_ADMIN_EMAIL not set in .env")
        sys.exit(1)
    if not settings.ROOT_ADMIN_PASSWORD:
        print("[SEED ADMIN ERROR] ROOT_ADMIN_PASSWORD not set in .env")
        sys.exit(1)
    if not settings.ROOT_ADMIN_TOTP_SECRET:
        print("[SEED ADMIN ERROR] ROOT_ADMIN_TOTP_SECRET not set in .env")
        sys.exit(1)
    if not is_valid_totp_secret(settings.ROOT_ADMIN_TOTP_SECRET):
        print("[SEED ADMIN ERROR] ROOT_ADMIN_TOTP_SECRET must be valid base32.")
        print("  Generate one: python -c \"import pyotp; print(pyotp.random_base32())\"")
        sys.exit(1)

    totp_secret = normalize_totp_secret(settings.ROOT_ADMIN_TOTP_SECRET)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.role == UserRole.ROOT_ADMIN).first()
        if existing:
            if existing.totp_secret != totp_secret:
                existing.totp_secret = totp_secret
                existing.totp_enabled = True
                db.commit()
                print(f"[SEED ADMIN] Updated TOTP secret for: {existing.email}")
            else:
                print(f"[SEED ADMIN] Root Admin already exists: {existing.email}")
            print(f"[SEED ADMIN] TOTP secret: {totp_secret}")
            print("[SEED ADMIN] Add this secret to your authenticator app (manual entry).")
            return

        # Root admin can belong to GCTU or the first available university
        university = db.query(University).filter(University.is_active == True).first()
        if not university:
            print("[SEED ADMIN ERROR] No active university found. Run seed_data.py first.")
            sys.exit(1)

        admin = User(
            university_id=university.id,
            email=settings.ROOT_ADMIN_EMAIL.lower(),
            username="root_admin",
            full_name="Root Administrator",
            hashed_password=hash_password(settings.ROOT_ADMIN_PASSWORD),
            role=UserRole.ROOT_ADMIN,
            status=AccountStatus.ACTIVE,
            totp_secret=totp_secret,
            totp_enabled=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        print(f"[SEED ADMIN] Root Admin created: {admin.email}")
        print(f"[SEED ADMIN] TOTP secret: {totp_secret}")
        print("[SEED ADMIN] Configure your authenticator app with the TOTP secret above.")
        print("[SEED ADMIN] DELETE this script after successful first run in production.")

    except Exception as e:
        db.rollback()
        print(f"[SEED ADMIN ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
