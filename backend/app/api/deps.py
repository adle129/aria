from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.user import USER_ROLE_KB_ADMIN, User
from app.services.auth_service import AuthService

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    settings = get_settings()
    if not settings.auth_enabled:
        return None
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail={"code": 401, "msg": "未登录"})
    user = AuthService(settings).resolve_user_from_token(db, credentials.credentials)
    if user is None:
        raise HTTPException(status_code=401, detail={"code": 401, "msg": "未登录"})
    return user


def resolve_owner_id(current_user: User | None = Depends(get_current_user)) -> str | None:
    return current_user.id if current_user else None


def require_kb_admin(current_user: User | None = Depends(get_current_user)) -> User | None:
    settings = get_settings()
    if not settings.auth_enabled:
        return None
    if current_user is None:
        raise HTTPException(status_code=401, detail={"code": 401, "msg": "未登录"})
    if current_user.role != USER_ROLE_KB_ADMIN:
        raise HTTPException(
            status_code=403,
            detail={"code": 403, "msg": "需要资料库管理员权限"},
        )
    return current_user
