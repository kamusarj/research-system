from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.identity import Principal
from app.core.runtime_controls import rate_limiter
from app.db import get_db
from app.models import ServiceAccount, User
from app.schemas.auth import (
    AuthConfigRead,
    AuthStateRead,
    LoginRequest,
    PasswordChange,
    ServiceAccountCreate,
    ServiceAccountCreated,
    ServiceAccountRead,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.services.auth import (
    authenticate_user,
    change_own_password,
    create_service_account,
    create_session,
    create_user,
    get_user,
    local_user,
    revoke_service_account,
    revoke_session,
    serialize_service_account,
    serialize_user,
    update_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _principal(request: Request) -> Principal:
    principal = getattr(request.state, "principal", None)
    if principal is None:
        raise HTTPException(401, "Authentication is required")
    return principal


def _set_auth_cookies(response: Response, token: str, csrf_token: str) -> None:
    max_age = max(1, settings.auth_session_hours) * 3600
    response.set_cookie(
        settings.auth_cookie_name,
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )
    response.set_cookie(
        settings.auth_csrf_cookie_name,
        csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    # Trình duyệt chỉ chấp nhận xóa cookie __Host- khi lệnh xóa cũng có Secure.
    for name, http_only in (
        (settings.auth_cookie_name, True),
        (settings.auth_csrf_cookie_name, False),
    ):
        response.delete_cookie(
            name,
            path="/",
            secure=settings.auth_cookie_secure,
            httponly=http_only,
            samesite=settings.auth_cookie_samesite,
        )


@router.get("/config", response_model=AuthConfigRead)
def config() -> AuthConfigRead:
    return AuthConfigRead(
        enabled=settings.auth_enabled,
        mode=settings.auth_mode,
        csrf_cookie_name=settings.auth_csrf_cookie_name,
    )


LOGIN_FAILURE_BUCKET = "auth-login-account"


@router.post("/login", response_model=AuthStateRead)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthStateRead:
    if not settings.auth_enabled:
        raise HTTPException(409, "Authentication is disabled in trusted local mode")
    # Giới hạn theo IP có thể bị vượt khi IP thật đến từ header proxy; giới hạn thêm số lần
    # đăng nhập SAI cho từng tài khoản để chặn dò mật khẩu.
    window = max(1, settings.rate_limit_window_seconds)
    failures = rate_limiter.recent(LOGIN_FAILURE_BUCKET, data.email, window)
    if settings.rate_limit_enabled and failures >= max(1, settings.auth_login_attempts_per_window):
        raise HTTPException(429, "Too many failed sign-in attempts for this account")
    user = authenticate_user(db, data.email, data.password)
    if user is None:
        rate_limiter.record(LOGIN_FAILURE_BUCKET, data.email)
        raise HTTPException(401, "Invalid email or password")
    created = create_session(db, user)
    _set_auth_cookies(response, created.token, created.csrf_token)
    return AuthStateRead(enabled=True, user=serialize_user(user))


@router.get("/me", response_model=AuthStateRead)
def me(request: Request) -> AuthStateRead:
    if not settings.auth_enabled:
        return AuthStateRead(enabled=False, user=local_user())
    principal = _principal(request)
    return AuthStateRead(
        enabled=True,
        user=UserRead(
            id=principal.id,
            name=principal.name,
            email=principal.email,
            role=principal.role,
            active=True,
            password_configured=True,
        ),
    )


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    principal = _principal(request)
    if settings.auth_enabled and principal.session_id:
        revoke_session(db, principal.session_id, actor=principal.id)
    _clear_auth_cookies(response)
    response.status_code = 204
    return response


@router.post("/me/password", status_code=204)
def change_password(
    data: PasswordChange, request: Request, db: Session = Depends(get_db)
) -> Response:
    if not settings.auth_enabled:
        raise HTTPException(409, "Authentication is disabled in trusted local mode")
    principal = _principal(request)
    if principal.auth_kind == "service":
        raise HTTPException(403, "Service accounts have no password")
    changed = change_own_password(
        db,
        user_id=principal.id,
        session_id=principal.session_id,
        current=data.current_password,
        new=data.new_password,
    )
    if not changed:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "PASSWORD_INCORRECT",
                    "message": "Mật khẩu hiện tại không đúng",
                }
            },
        )
    return Response(status_code=204)


@router.get("/users", response_model=list[UserRead])
def users(db: Session = Depends(get_db)) -> list[UserRead]:
    return [serialize_user(user) for user in db.scalars(select(User).order_by(User.email))]


@router.post("/users", response_model=UserRead, status_code=201)
def add_user(
    data: UserCreate, request: Request, db: Session = Depends(get_db)
) -> UserRead:
    actor = _principal(request)
    return serialize_user(create_user(db, data, actor=actor.id))


@router.patch("/users/{user_id}", response_model=UserRead)
def edit_user(
    user_id: str,
    data: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> UserRead:
    actor = _principal(request)
    user = get_user(db, user_id)
    return serialize_user(update_user(db, user, data, actor=actor.id, actor_id=actor.id))


@router.get("/service-accounts", response_model=list[ServiceAccountRead])
def service_accounts(db: Session = Depends(get_db)) -> list[ServiceAccountRead]:
    return [
        serialize_service_account(account)
        for account in db.scalars(select(ServiceAccount).order_by(ServiceAccount.created_at.desc()))
    ]


@router.post(
    "/service-accounts", response_model=ServiceAccountCreated, status_code=201
)
def add_service_account(
    data: ServiceAccountCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> ServiceAccountCreated:
    actor = _principal(request)
    return create_service_account(db, data, actor=actor.id)


@router.delete("/service-accounts/{account_id}", status_code=204)
def delete_service_account(
    account_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    actor = _principal(request)
    revoke_service_account(db, account_id, actor=actor.id)
    return Response(status_code=204)
