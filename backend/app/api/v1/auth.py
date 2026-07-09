from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_kb_admin
from app.config import get_settings
from app.database import get_db
from app.models.user import USER_ROLES, User
from app.schemas.auth import ChangePasswordRequest, CreateUserRequest, LoginRequest, UpdateUserRequest
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
    svc = AuthService(settings)
    user = svc.authenticate(db, body.username, body.password)
    if user is None:
        return JSONResponse(
            status_code=401,
            content={"code": 401, "msg": "用户名或密码错误"},
        )
    token, expires_at = svc.create_access_token(user)
    return {
        "code": 200,
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": expires_at.isoformat(),
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


@router.post("/refresh")
def refresh_token(current_user: User = Depends(get_current_user)):
    """Issue a new token for the authenticated user (token renewal)."""
    if current_user is None:
        return JSONResponse(status_code=401, content={"code": 401, "msg": "未登录"})
    settings = get_settings()
    svc = AuthService(settings)
    token, expires_at = svc.create_access_token(current_user)
    return {
        "code": 200,
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": expires_at.isoformat(),
        },
    }


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user is None:
        return JSONResponse(status_code=401, content={"code": 401, "msg": "未登录"})
    settings = get_settings()
    try:
        AuthService(settings).change_password(db, current_user, body.old_password, body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": 400, "msg": str(e)}) from e
    return {"code": 200, "data": {"ok": True}}


# ── User management (kb_admin only) ────────────────────────────────────────

@router.get("/users")
def list_users(
    _admin: User | None = Depends(require_kb_admin),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    users = AuthService(settings).list_users(db)
    return {"code": 200, "data": [AuthService.user_detail(u) for u in users]}


@router.post("/users")
def create_user(
    body: CreateUserRequest,
    _admin: User | None = Depends(require_kb_admin),
    db: Session = Depends(get_db),
):
    if body.role not in USER_ROLES:
        raise HTTPException(status_code=422, detail={"code": 422, "msg": f"无效角色: {body.role}"})
    settings = get_settings()
    try:
        user = AuthService(settings).create_user(
            db,
            username=body.username,
            password=body.password,
            display_name=body.display_name,
            role=body.role,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": 409, "msg": str(e)}) from e
    return {"code": 200, "data": AuthService.user_detail(user)}


@router.patch("/users/{user_id}")
def update_user(
    user_id: str,
    body: UpdateUserRequest,
    _admin: User | None = Depends(require_kb_admin),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    try:
        user = AuthService(settings).update_user(
            db,
            user_id,
            display_name=body.display_name,
            role=body.role,
            is_active=body.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"code": 404, "msg": str(e)}) from e
    return {"code": 200, "data": AuthService.user_detail(user)}
