#!/usr/bin/env python3
"""Create initial admin / engineer users (R1-AUTH07 helper)."""

from __future__ import annotations

import argparse
import sys

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.models.user import USER_ROLE_KB_ADMIN, USER_ROLE_QUOTE_ENGINEER
from app.services.auth_service import AuthService


def main() -> int:
    parser = argparse.ArgumentParser(description="Create ARIA user account")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument(
        "--role",
        choices=[USER_ROLE_QUOTE_ENGINEER, USER_ROLE_KB_ADMIN],
        default=USER_ROLE_QUOTE_ENGINEER,
    )
    args = parser.parse_args()

    settings = get_settings()
    if not settings.auth_enabled:
        print("AUTH_ENABLED=false — enable auth before creating users", file=sys.stderr)
        return 1

    init_db()
    db = SessionLocal()
    try:
        user = AuthService(settings).create_user(
            db,
            username=args.username,
            password=args.password,
            display_name=args.display_name,
            role=args.role,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        db.close()

    print(f"Created user {user.username} ({user.role}) id={user.id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
