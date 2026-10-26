from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PlanModel(BaseModel):
    slug: str
    display_name: str


class ChatGPTPlanStatus(BaseModel):
    enabled: bool
    # local: tự đăng ký, chỉ dùng được từ trình duyệt trên máy chạy API; partner: client OpenAI cấp.
    mode: Literal["local", "partner"]
    status: Literal["not_connected", "active", "signed_out", "reauth_required", "plan_disabled"]
    email: str | None = None
    model: str | None = None
    models: list[PlanModel] = Field(default_factory=list)
    use_by_default: bool = True
    last_error_code: str | None = None
    connected_at: datetime | None = None
    last_used_at: datetime | None = None
    usage_url: str


class ChatGPTPlanStart(BaseModel):
    authorize_url: str


class ChatGPTPlanComplete(BaseModel):
    state: str = Field(min_length=16, max_length=200)
    code: str | None = Field(default=None, max_length=4096)
    client_id: str | None = Field(default=None, max_length=200)
    error: str | None = Field(default=None, max_length=100)


class ChatGPTPlanPreferences(BaseModel):
    model: str | None = Field(default=None, min_length=1, max_length=200)
    use_by_default: bool | None = None


class ChatGPTPlanDisconnect(BaseModel):
    # True = xóa luôn đăng ký (để kết nối một tài khoản ChatGPT khác).
    forget: bool = False


class ChatGPTPlanDisconnectResult(BaseModel):
    remote_revoked: bool
    connection: ChatGPTPlanStatus
