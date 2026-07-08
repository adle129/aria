from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.auth_enabled:
        return JSONResponse(
            status_code=503,
            content={"code": 503, "msg": "认证未启用"},
        )
    user = AuthService(settings).authenticate(db, body.username, body.password)
    if user is None:
        return JSONResponse(
            status_code=401,
            content={"code": 401, "msg": "用户名或密码错误"},
        )
    token = AuthService(settings).create_access_token(user)
    return {
        "code": 200,
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "user": AuthService.user_public(user),
        },
    }


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    if current_user is None:
        return JSONResponse(status_code=401, content={"code": 401, "msg": "未登录"})
    return {"code": 200, "data": AuthService.user_public(current_user)}


@router.post("/logout")
def logout(_current_user: User | None = Depends(get_current_user)):
    return {"code": 200, "data": {"ok": True}}
