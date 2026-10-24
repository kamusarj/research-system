from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from pwdlib import PasswordHash
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.identity import Principal
from app.models import AuditEvent, AuthSession, ServiceAccount, User, utcnow
from app.schemas.auth import (
    ServiceAccountCreate,
    ServiceAccountCreated,
    ServiceAccountRead,
    UserCreate,
    UserRead,
    UserUpdate,
)

password_hash = PasswordHash.recommended()
_DUMMY_HASH = password_hash.hash("not-a-real-user-password")
_ZERO_ENTITY_ID = "00000000-0000-0000-0000-000000000000"


@dataclass(frozen=True, slots=True)
class CreatedSession:
    principal: Principal
    token: str
    csrf_token: str


_SERVICE_TOKEN_PREFIX = "research_svc_"


def normalize_email(value: str) -> str:
    return value.strip().casefold()


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def serialize_user(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        active=user.active,
        password_configured=bool(user.password_hash),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def local_user() -> UserRead:
    return UserRead(
        id="local-user",
        name="Chủ sở hữu cục bộ",
        email="local@research.invalid",
        role="owner",
        active=True,
        password_configured=False,
    )


def serialize_service_account(account: ServiceAccount) -> ServiceAccountRead:
    return ServiceAccountRead(
        id=account.id,
        name=account.name,
        source_namespace=account.source_namespace,
        token_prefix=account.token_prefix,
        scopes=account.scopes or [],
        active=account.active,
        expires_at=account.expires_at,
        revoked_at=account.revoked_at,
        last_used_at=account.last_used_at,
        created_by=account.created_by,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


def create_service_account(
    db: Session, data: ServiceAccountCreate, *, actor: str
) -> ServiceAccountCreated:
    now = utcnow()
    if data.expires_at is not None and _aware(data.expires_at) <= now:
        raise HTTPException(422, "Service account expiry must be in the future")
    raw_token = _SERVICE_TOKEN_PREFIX + secrets.token_urlsafe(32)
    account = ServiceAccount(
        name=data.name.strip(),
        source_namespace=data.source_namespace,
        token_hash=hash_token(raw_token),
        token_prefix=raw_token[:16],
        scopes=list(data.scopes),
        active=True,
        expires_at=data.expires_at,
        created_by=actor,
    )
    db.add(account)
    db.flush()
    db.add(
        AuditEvent(
            entity_type="service_account",
            entity_id=account.id,
            action="auth.service_account.created",
            actor=actor,
            payload={
                "namespace_hash": hash_token(account.source_namespace),
                "scopes": sorted(account.scopes),
            },
        )
    )
    db.commit()
    db.refresh(account)
    return ServiceAccountCreated(**serialize_service_account(account).model_dump(), token=raw_token)


def resolve_service_account(db: Session, raw_token: str) -> Principal | None:
    if not raw_token.startswith(_SERVICE_TOKEN_PREFIX) or len(raw_token) > 256:
        return None
    account = db.scalar(
        select(ServiceAccount).where(ServiceAccount.token_hash == hash_token(raw_token))
    )
    if account is None or not account.active or account.revoked_at is not None:
        return None
    if account.expires_at is not None and _aware(account.expires_at) <= utcnow():
        return None
    account.last_used_at = utcnow()
    db.commit()
    return Principal(
        id=account.id,
        name=account.name,
        email="service-account@research.invalid",
        role="researcher",
        auth_kind="service",
        scopes=tuple(account.scopes or []),
        source_namespace=account.source_namespace,
    )


def revoke_service_account(db: Session, account_id: str, *, actor: str) -> None:
    account = db.get(ServiceAccount, account_id)
    if account is None:
        raise HTTPException(404, "Service account not found")
    if account.revoked_at is None:
        account.active = False
        account.revoked_at = utcnow()
        db.add(
            AuditEvent(
                entity_type="service_account",
                entity_id=account.id,
                action="auth.service_account.revoked",
                actor=actor,
                payload={"namespace_hash": hash_token(account.source_namespace)},
            )
        )
        db.commit()


def create_user(db: Session, data: UserCreate, *, actor: str) -> User:
    email = normalize_email(data.email)
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(409, "A user with this email already exists")
    user = User(
        name=data.name.strip(),
        email=email,
        role=data.role,
        active=True,
        password_hash=password_hash.hash(data.password),
        password_changed_at=utcnow(),
    )
    db.add(user)
    db.flush()
    db.add(
        AuditEvent(
            entity_type="user",
            entity_id=user.id,
            action="auth.user.created",
            actor=actor,
            payload={"role": user.role},
        )
    )
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session, user: User, data: UserUpdate, *, actor: str, actor_id: str
) -> User:
    if user.id == actor_id and (
        data.active is False or (data.role is not None and data.role != "owner")
    ):
        raise HTTPException(409, "An owner cannot deactivate or demote the current session")
    old_role = user.role
    old_active = user.active
    if data.name is not None:
        user.name = data.name.strip()
    if data.role is not None:
        user.role = data.role
    if data.active is not None:
        user.active = data.active
    password_changed = data.password is not None
    if data.password is not None:
        user.password_hash = password_hash.hash(data.password)
        user.password_changed_at = utcnow()

    if old_role == "owner" and (user.role != "owner" or not user.active):
        other_owners = int(
            db.scalar(
                select(func.count())
                .select_from(User)
                .where(User.id != user.id, User.role == "owner", User.active.is_(True))
            )
            or 0
        )
        if other_owners == 0:
            raise HTTPException(409, "At least one active owner is required")

    if password_changed or (old_active and not user.active):
        db.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )
    db.add(
        AuditEvent(
            entity_type="user",
            entity_id=user.id,
            action="auth.user.updated",
            actor=actor,
            payload={
                "role": user.role,
                "active": user.active,
                "password_changed": password_changed,
            },
        )
    )
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    normalized = normalize_email(email)
    user = db.scalar(select(User).where(func.lower(User.email) == normalized))
    candidate_hash = user.password_hash if user and user.password_hash else _DUMMY_HASH
    verified = password_hash.verify(password, candidate_hash)
    if not user or not verified or not user.active or not user.password_hash:
        db.add(
            AuditEvent(
                entity_type="auth",
                entity_id=_ZERO_ENTITY_ID,
                action="auth.login.failed",
                actor="anonymous",
                payload={},
            )
        )
        db.commit()
        return None
    return user


def change_own_password(
    db: Session, *, user_id: str, session_id: str | None, current: str, new: str
) -> bool:
    """Đổi mật khẩu của chính người dùng; giữ phiên hiện tại, thu hồi mọi phiên khác."""
    user = db.get(User, user_id)
    candidate_hash = user.password_hash if user and user.password_hash else _DUMMY_HASH
    verified = password_hash.verify(current, candidate_hash)
    if user is None or not user.active or not user.password_hash or not verified:
        db.add(
            AuditEvent(
                entity_type="user",
                entity_id=user.id if user else _ZERO_ENTITY_ID,
                action="auth.password.change_failed",
                actor=user_id,
                payload={},
            )
        )
        db.commit()
        return False
    user.password_hash = password_hash.hash(new)
    user.password_changed_at = utcnow()
    revoke_others = update(AuthSession).where(
        AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)
    )
    if session_id is not None:
        revoke_others = revoke_others.where(AuthSession.id != session_id)
    db.execute(revoke_others.values(revoked_at=utcnow()))
    db.add(
        AuditEvent(
            entity_type="user",
            entity_id=user.id,
            action="auth.password.changed",
            actor=user.id,
            payload={},
        )
    )
    db.commit()
    return True


def create_session(db: Session, user: User) -> CreatedSession:
    token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    record = AuthSession(
        user_id=user.id,
        token_hash=hash_token(token),
        csrf_hash=hash_token(csrf_token),
        expires_at=utcnow() + timedelta(hours=max(1, settings.auth_session_hours)),
    )
    db.add(record)
    db.flush()
    db.add(
        AuditEvent(
            entity_type="auth_session",
            entity_id=record.id,
            action="auth.login.succeeded",
            actor=user.id,
            payload={"role": user.role},
        )
    )
    db.commit()
    return CreatedSession(
        principal=Principal(user.id, user.name, user.email, user.role, record.id, record.csrf_hash),
        token=token,
        csrf_token=csrf_token,
    )


def resolve_session(db: Session, raw_token: str) -> Principal | None:
    row = db.execute(
        select(AuthSession, User)
        .join(User, User.id == AuthSession.user_id)
        .where(AuthSession.token_hash == hash_token(raw_token))
    ).one_or_none()
    if row is None:
        return None
    session, user = row
    if session.revoked_at is not None or not user.active or _aware(session.expires_at) <= utcnow():
        return None
    return Principal(user.id, user.name, user.email, user.role, session.id, session.csrf_hash)


def revoke_session(db: Session, session_id: str, *, actor: str) -> None:
    record = db.get(AuthSession, session_id)
    if record is None or record.revoked_at is not None:
        return
    record.revoked_at = utcnow()
    db.add(
        AuditEvent(
            entity_type="auth_session",
            entity_id=record.id,
            action="auth.logout",
            actor=actor,
            payload={},
        )
    )
    db.commit()


def get_user(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    return user
