#!/usr/bin/env python3
"""Seed default admin + engineer accounts (idempotent).

Used by Aliyun staging / offline install so operators can log in without
manual docker cp of create_admin.py.

Env (optional):
  SEED_ADMIN_USERNAME / SEED_ADMIN_PASSWORD / SEED_ADMIN_DISPLAY_NAME
  SEED_ENGINEER_USERNAME / SEED_ENGINEER_PASSWORD / SEED_ENGINEER_DISPLAY_NAME
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Allow `python /tmp/seed_default_users.py` inside the container
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path and (_ROOT / "app").is_dir():
    sys.path.insert(0, str(_ROOT))
elif "/app" not in sys.path and Path("/app/app").is_dir():
    sys.path.insert(0, "/app")

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.models.user import USER_ROLE_KB_ADMIN, USER_ROLE_QUOTE_ENGINEER
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


def _ensure_user(
    auth: AuthService,
    db,
    *,
    username: str,
    password: str,
    display_name: str,
    role: str,
) -> str:
    existing = UserRepository(db).get_by_username(username)
    if existing:
        return f"exists\t{username}\t{existing.role}\tid={existing.id}"
    user = auth.create_user(
        db,
        username=username,
        password=password,
        display_name=display_name,
        role=role,
    )
    return f"created\t{user.username}\t{user.role}\tid={user.id}"


def seed_default_users(
    *,
    admin_username: str,
    admin_password: str,
    admin_display_name: str,
    engineer_username: str,
    engineer_password: str,
    engineer_display_name: str,
    db=None,
) -> list[str]:
    settings = get_settings()
    if not settings.auth_enabled:
        raise RuntimeError("AUTH_ENABLED=false — enable auth before seeding users")

    owns_session = db is None
    if owns_session:
        init_db()
        db = SessionLocal()
    lines: list[str] = []
    try:
        auth = AuthService(settings)
        lines.append(
            _ensure_user(
                auth,
                db,
                username=admin_username,
                password=admin_password,
                display_name=admin_display_name,
                role=USER_ROLE_KB_ADMIN,
            )
        )
        lines.append(
            _ensure_user(
                auth,
                db,
                username=engineer_username,
                password=engineer_password,
                display_name=engineer_display_name,
                role=USER_ROLE_QUOTE_ENGINEER,
            )
        )
        if owns_session:
            db.commit()
    finally:
        if owns_session:
            db.close()
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed default ARIA admin + engineer users")
    parser.add_argument(
        "--admin-username",
        default=os.getenv("SEED_ADMIN_USERNAME", "admin"),
    )
    parser.add_argument(
        "--admin-password",
        default=os.getenv("SEED_ADMIN_PASSWORD", "admin123"),
    )
    parser.add_argument(
        "--admin-display-name",
        default=os.getenv("SEED_ADMIN_DISPLAY_NAME", "系统管理员"),
    )
    parser.add_argument(
        "--engineer-username",
        default=os.getenv("SEED_ENGINEER_USERNAME", "engineer"),
    )
    parser.add_argument(
        "--engineer-password",
        default=os.getenv("SEED_ENGINEER_PASSWORD", "engineer123"),
    )
    parser.add_argument(
        "--engineer-display-name",
        default=os.getenv("SEED_ENGINEER_DISPLAY_NAME", "报价工程师"),
    )
    args = parser.parse_args()

    try:
        lines = seed_default_users(
            admin_username=args.admin_username,
            admin_password=args.admin_password,
            admin_display_name=args.admin_display_name,
            engineer_username=args.engineer_username,
            engineer_password=args.engineer_password,
            engineer_display_name=args.engineer_display_name,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
