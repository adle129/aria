from datetime import datetime, timedelta, timezone
from typing import Any
import logging

import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.user import USER_ROLE_QUOTE_ENGINEER, USER_ROLES, User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserDetail, UserPublic

logger = logging.getLogger(__name__)
_pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class AuthService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def hash_password(self, password: str) -> str:
        return _pwd_context.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        return _pwd_context.verify(password, password_hash)

    def create_user(
        self,
        db: Session,
        *,
        username: str,
        password: str,
        display_name: str,
        role: str = USER_ROLE_QUOTE_ENGINEER,
    ) -> User:
        repo = UserRepository(db)
        if repo.get_by_username(username):
            raise ValueError(f"用户名已存在: {username}")
        user = User(
            username=username,
            password_hash=self.hash_password(password),
            display_name=display_name,
            role=role,
        )
        return repo.create(user)

    def authenticate(self, db: Session, username: str, password: str) -> User | None:
        user = UserRepository(db).get_by_username(username)
        if not user:
            logger.info("auth_login_fail username=%r reason=not_found", username)
            return None
        if not user.is_active:
            logger.info(
                "auth_login_fail username=%r user_id=%s reason=inactive",
                username,
                user.id,
            )
            return None
        if not self.verify_password(password, user.password_hash):
            logger.info(
                "auth_login_fail username=%r user_id=%s reason=bad_creds",
                username,
                user.id,
            )
            return None
        logger.info(
            "auth_login_ok username=%r user_id=%s role=%s",
            username,
            user.id,
            user.role,
        )
        return user

    def token_expire_time(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(hours=self.settings.jwt_expire_hours)

    def create_access_token(self, user: User) -> tuple[str, datetime]:
        expire = self.token_expire_time()
        payload = {"sub": user.id, "exp": expire}
        token = jwt.encode(payload, self.settings.jwt_secret, algorithm="HS256")
        return token, expire

    def resolve_user_from_token(self, db: Session, token: str) -> User | None:
        try:
            payload = jwt.decode(token, self.settings.jwt_secret, algorithms=["HS256"])
        except jwt.PyJWTError:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = UserRepository(db).get_by_id(str(user_id))
        if not user or not user.is_active:
            return None
        return user

    def change_password(self, db: Session, user: User, old_password: str, new_password: str) -> None:
        if not self.verify_password(old_password, user.password_hash):
            raise ValueError("原密码错误")
        user.password_hash = self.hash_password(new_password)
        UserRepository(db).save(user)

    def list_users(self, db: Session) -> list[User]:
        return UserRepository(db).list_all()

    def update_user(
        self,
        db: Session,
        user_id: str,
        *,
        display_name: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> User:
        repo = UserRepository(db)
        user = repo.get_by_id(user_id)
        if user is None:
            raise ValueError(f"用户不存在: {user_id}")
        if display_name is not None:
            user.display_name = display_name
        if role is not None:
            if role not in USER_ROLES:
                raise ValueError(f"无效角色: {role}")
            user.role = role
        if is_active is not None:
            user.is_active = is_active
        return repo.save(user)

    @staticmethod
    def user_public(user: User) -> dict[str, Any]:
        return UserPublic(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
        ).model_dump()

    @staticmethod
    def user_detail(user: User) -> dict[str, Any]:
        return UserDetail(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        ).model_dump()
