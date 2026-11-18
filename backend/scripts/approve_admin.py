"""Approve an admin who registered on the Register page (Admin tab).

Needed for the very first admin, because there is no existing admin yet to approve them in the dashboard.

Usage (from backend/):
    python -m scripts.approve_admin --email admin@example.com
    python -m scripts.approve_admin --list        # show pending admins
"""
import argparse
import sys

from app.database import SessionLocal
from app.models import AdminProfile, User
from app.models.enums import UserRole, VerificationStatus


def main() -> None:
    parser = argparse.ArgumentParser(description="Approve a self-registered admin")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--email", help="email or phone number the admin registered with")
    group.add_argument("--list", action="store_true", help="list admins awaiting approval")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.list:
            pending = (db.query(User).join(AdminProfile)
                       .filter(AdminProfile.verification_status == VerificationStatus.PENDING.value).all())
            if not pending:
                print("No admins are waiting for approval.")
            for u in pending:
                print(f"{u.email or '-'} | {u.phone} | {u.admin_profile.employee_id} | {u.admin_profile.hospital_name}")
            return

        ident = args.email.strip()
        user = db.query(User).filter((User.email == ident.lower()) | (User.phone == ident)).first()
        if user is None:
            sys.exit(f"Error: no account found for {ident}. Register on the Admin tab first.")
        if user.role != UserRole.ADMIN.value:
            sys.exit(f"Error: {ident} is registered as {user.role}, not ADMIN.")
        user.is_verified = True
        user.is_active = True
        if user.admin_profile is not None:
            user.admin_profile.verification_status = VerificationStatus.VERIFIED.value
        db.commit()
        note = "" if user.phone_verified else " Their phone is not verified yet: they must enter the code at login."
        print(f"Approved admin: {user.email or user.phone}.{note}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
