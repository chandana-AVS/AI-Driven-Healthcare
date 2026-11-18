"""Create (or reset) an administrator account.

Usage (from backend/):
    python -m scripts.create_admin --email admin@example.com --name "System Admin"
The password is prompted for interactively, or read from the ADMIN_PASSWORD environment variable.
"""
import argparse
import getpass
import os
import sys

from app.database import SessionLocal
from app.models import User
from app.models.enums import UserRole
from app.utils.security import hash_password
from app.utils.validators import validate_password_strength


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="System Administrator")
    args = parser.parse_args()

    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Admin password: ")
    try:
        validate_password_strength(password)
    except ValueError as exc:
        sys.exit(f"Error: {exc}")

    db = SessionLocal()
    try:
        email = args.email.lower()
        user = db.query(User).filter(User.email == email).first()
        if user and user.role != UserRole.ADMIN.value:
            sys.exit("Error: a non-admin account already uses this email")
        if user is None:
            user = User(full_name=args.name, email=email, role=UserRole.ADMIN.value, preferred_language="en")
            db.add(user)
        user.password_hash = hash_password(password)
        user.is_active = True
        user.is_verified = True
        db.commit()
        print(f"Admin account ready: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
