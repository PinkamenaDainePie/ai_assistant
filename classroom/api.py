# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from classroom.auth import decode_access_token
from classroom.config import (
    CLASSROOM_ALLOW_LOCAL_LOGIN,
    CLASSROOM_ALLOW_REGISTER,
    CLASSROOM_SWUFE_CLIENT_ID,
    CLASSROOM_SWUFE_SSO_MOCK,
    classroom_enabled,
)
from classroom import sso_swufe
from classroom.schemas import (
    AuthConfigResponse,
    ClassInfo,
    LoginRequest,
    LoginResponse,
    PlaythroughCreate,
    PlaythroughListResponse,
    PlaythroughPublic,
    PlaythroughReviewRequest,
    PlaythroughUpdate,
    RegisterRequest,
    UserPublic,
)
from classroom import service

router = APIRouter(prefix="/api", tags=["classroom"])
_bearer = HTTPBearer(auto_error=False)


def _require_enabled() -> None:
    if not classroom_enabled():
        raise HTTPException(status_code=503, detail="课堂账号服务未启用（需配置 DATABASE_URL）")


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> UserPublic:
    _require_enabled()
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_access_token(creds.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="登录已失效")
    return service.get_user_by_id(UUID(str(payload["sub"])))


def require_teacher(user: UserPublic = Depends(get_current_user)) -> UserPublic:
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="需要教师权限")
    return user


@router.get("/auth/config", response_model=AuthConfigResponse)
def auth_config() -> AuthConfigResponse:
    enabled = classroom_enabled()
    return AuthConfigResponse(
        enabled=enabled,
        allow_register=CLASSROOM_ALLOW_REGISTER and enabled,
        swufe_sso_enabled=enabled and sso_swufe.swufe_sso_ready(),
        allow_local_login=CLASSROOM_ALLOW_LOCAL_LOGIN,
    )


@router.get("/auth/sso/swufe/start")
def auth_sso_swufe_start() -> RedirectResponse:
    _require_enabled()
    if not sso_swufe.swufe_sso_ready():
        raise HTTPException(status_code=503, detail="西南财大 SSO 未配置")
    if CLASSROOM_SWUFE_SSO_MOCK and not CLASSROOM_SWUFE_CLIENT_ID:
        return RedirectResponse(url="/api/auth/sso/swufe/mock?role=student", status_code=302)
    return RedirectResponse(url=sso_swufe.build_authorize_url(), status_code=302)


@router.get("/auth/sso/swufe/mock")
def auth_sso_swufe_mock(role: str = Query(default="student")) -> RedirectResponse:
    _require_enabled()
    if not CLASSROOM_SWUFE_SSO_MOCK:
        raise HTTPException(status_code=404, detail="SSO Mock 未启用")
    parsed = sso_swufe.mock_profile(role)
    out = service.upsert_swufe_user(
        swufe_id=str(parsed.get("swufe_id") or ""),
        email=str(parsed.get("email") or ""),
        name=str(parsed.get("name") or ""),
        role=str(parsed.get("role") or "student"),
        student_id=parsed.get("student_id"),
    )
    return RedirectResponse(url=sso_swufe.frontend_callback_url(out["access_token"]), status_code=302)


@router.get("/auth/sso/swufe/callback")
def auth_sso_swufe_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
) -> RedirectResponse:
    _require_enabled()
    if error:
        raise HTTPException(status_code=400, detail=f"SSO 授权失败: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="缺少 code 或 state")
    try:
        parsed = sso_swufe.complete_oauth_login(code, state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    out = service.upsert_swufe_user(
        swufe_id=str(parsed.get("swufe_id") or ""),
        email=str(parsed.get("email") or ""),
        name=str(parsed.get("name") or ""),
        role=str(parsed.get("role") or "student"),
        student_id=parsed.get("student_id"),
    )
    return RedirectResponse(url=sso_swufe.frontend_callback_url(out["access_token"]), status_code=302)


@router.post("/auth/login", response_model=LoginResponse)
def auth_login(body: LoginRequest) -> LoginResponse:
    _require_enabled()
    if not CLASSROOM_ALLOW_LOCAL_LOGIN:
        raise HTTPException(status_code=403, detail="请使用校园账号登录")
    out = service.login_user(body.email, body.password)
    return LoginResponse(access_token=out["access_token"], user=out["user"])


@router.post("/auth/register", response_model=UserPublic)
def auth_register(body: RegisterRequest) -> UserPublic:
    _require_enabled()
    if not CLASSROOM_ALLOW_REGISTER:
        raise HTTPException(status_code=403, detail="注册未开放")
    return service.register_user(
        email=body.email,
        password=body.password,
        name=body.name,
        role=body.role,
        student_id=body.student_id,
    )


@router.get("/me", response_model=UserPublic)
def me(user: UserPublic = Depends(get_current_user)) -> UserPublic:
    return user


@router.post("/playthroughs", response_model=PlaythroughPublic)
def create_playthrough(
    body: PlaythroughCreate,
    user: UserPublic = Depends(get_current_user),
) -> PlaythroughPublic:
    if user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可创建游玩记录")
    return service.create_playthrough(user.id, body)


@router.get("/playthroughs/mine", response_model=PlaythroughListResponse)
def list_my_playthroughs(user: UserPublic = Depends(get_current_user)) -> PlaythroughListResponse:
    return PlaythroughListResponse(items=service.list_my_playthroughs(user.id))


@router.get("/playthroughs/{playthrough_id}", response_model=PlaythroughPublic)
def get_playthrough(
    playthrough_id: UUID,
    user: UserPublic = Depends(get_current_user),
) -> PlaythroughPublic:
    return service.get_my_playthrough(user.id, playthrough_id)


@router.patch("/playthroughs/{playthrough_id}", response_model=PlaythroughPublic)
def patch_playthrough(
    playthrough_id: UUID,
    body: PlaythroughUpdate,
    user: UserPublic = Depends(get_current_user),
) -> PlaythroughPublic:
    return service.update_playthrough(user.id, playthrough_id, body)


@router.get("/teacher/classes", response_model=List[ClassInfo])
def teacher_classes(teacher: UserPublic = Depends(require_teacher)) -> list[ClassInfo]:
    return service.list_teacher_classes(teacher.id)


@router.get("/teacher/playthroughs", response_model=PlaythroughListResponse)
def teacher_playthroughs(
    class_id: Optional[int] = None,
    scenario_code: Optional[str] = None,
    status: Optional[str] = None,
    teacher: UserPublic = Depends(require_teacher),
) -> PlaythroughListResponse:
    items = service.list_teacher_playthroughs(
        teacher.id,
        class_id=class_id,
        scenario_code=scenario_code,
        status=status,
    )
    return PlaythroughListResponse(items=items)


@router.get("/teacher/playthroughs/{playthrough_id}", response_model=PlaythroughPublic)
def teacher_playthrough_detail(
    playthrough_id: UUID,
    teacher: UserPublic = Depends(require_teacher),
) -> PlaythroughPublic:
    return service.get_teacher_playthrough(teacher.id, playthrough_id)


@router.patch("/teacher/playthroughs/{playthrough_id}/review", response_model=PlaythroughPublic)
def teacher_playthrough_review(
    playthrough_id: UUID,
    body: PlaythroughReviewRequest,
    teacher: UserPublic = Depends(require_teacher),
) -> PlaythroughPublic:
    return service.upsert_teacher_playthrough_review(teacher.id, playthrough_id, body)
