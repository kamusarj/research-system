from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

UserRole = Literal["owner", "researcher", "viewer"]
ServiceAccountScope = Literal["intake:submit", "intake:read-own", "research:run", "research:read"]


def _normalize_email(value: str) -> str:
    normalized = value.strip().casefold()
    if (
        len(normalized) > 320
        or normalized.count("@") != 1
        or not normalized.split("@", 1)[0]
        or "." not in normalized.split("@", 1)[1]
    ):
        raise ValueError("Enter a valid email address")
    return normalized


class AuthConfigRead(BaseModel):
    enabled: bool
    mode: str
    csrf_cookie_name: str


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=128)

    _email = field_validator("email")(_normalize_email)


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    role: UserRole = "researcher"
    password: str = Field(min_length=12, max_length=128)

    _email = field_validator("email")(_normalize_email)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    role: UserRole | None = None
    active: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=128)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class UserRead(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    active: bool
    password_configured: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AuthStateRead(BaseModel):
    enabled: bool
    user: UserRead


class ServiceAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_namespace: str = Field(
        min_length=1, max_length=120, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"
    )
    scopes: list[ServiceAccountScope] = Field(
        default_factory=lambda: ["intake:submit", "intake:read-own"],
        min_length=1,
        max_length=4,
    )
    expires_at: datetime | None = None

    @field_validator("scopes")
    @classmethod
    def unique_scopes(cls, value: list[ServiceAccountScope]) -> list[ServiceAccountScope]:
        if len(value) != len(set(value)):
            raise ValueError("Service account scopes must be unique")
        return value


class ServiceAccountRead(BaseModel):
    id: str
    name: str
    source_namespace: str
    token_prefix: str
    scopes: list[ServiceAccountScope]
    active: bool
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class ServiceAccountCreated(ServiceAccountRead):
    token: str
