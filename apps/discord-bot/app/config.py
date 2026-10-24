"""Configuration for the Discord gateway.

Secrets are read from `/run/secrets/<name>` when that file exists and from the environment
otherwise, matching how the API resolves its own credentials. A file-mounted secret is
preferred because it does not appear in `docker inspect` or a process listing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SECRETS_DIR = "/run/secrets"


def secrets_dir() -> Path:
    """Resolved per call so a deployment can point it elsewhere without a code change."""

    return Path(os.environ.get("SECRETS_DIR", DEFAULT_SECRETS_DIR))


def read_secret(name: str, default: str = "") -> str:
    path = secrets_dir() / name.casefold()
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return os.environ.get(name, default).strip()


def _id_set(raw: str) -> frozenset[str]:
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def _boolean(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    normalized = raw.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} phải có giá trị true hoặc false")


@dataclass(frozen=True, slots=True)
class BotConfig:
    discord_token: str
    api_base_url: str
    api_token: str
    namespace: str
    guild_ids: frozenset[str]
    channel_ids: frozenset[str]
    provider: str | None
    auto_approve_links: bool
    locale: str
    poll_interval_seconds: float
    poll_attempts: int
    request_timeout_seconds: float
    per_user_messages_per_minute: int

    @property
    def configured(self) -> bool:
        return bool(self.discord_token and self.api_token and self.guild_ids and self.channel_ids)

    def missing(self) -> list[str]:
        """Name what is absent, so a refusal to start is diagnosable without guesswork."""

        gaps: list[str] = []
        if not self.discord_token:
            gaps.append("DISCORD_BOT_TOKEN")
        if not self.api_token:
            gaps.append("RESEARCH_API_TOKEN")
        if not self.guild_ids:
            gaps.append("DISCORD_ALLOWED_GUILD_IDS")
        if not self.channel_ids:
            gaps.append("DISCORD_ALLOWED_CHANNEL_IDS")
        return gaps


def load_config() -> BotConfig:
    return BotConfig(
        discord_token=read_secret("DISCORD_BOT_TOKEN"),
        api_base_url=os.environ.get("RESEARCH_API_URL", "http://api:8000").rstrip("/"),
        api_token=read_secret("RESEARCH_API_TOKEN"),
        namespace=os.environ.get("DISCORD_INTAKE_NAMESPACE", "discord"),
        guild_ids=_id_set(os.environ.get("DISCORD_ALLOWED_GUILD_IDS", "")),
        channel_ids=_id_set(os.environ.get("DISCORD_ALLOWED_CHANNEL_IDS", "")),
        provider=os.environ.get("DISCORD_INTAKE_PROVIDER") or None,
        auto_approve_links=_boolean("DISCORD_AUTO_APPROVE_LINKS", True),
        # Sản phẩm chỉ hiển thị tiếng Việt; giữ trường này để tương thích cấu hình cũ.
        locale="vi",
        poll_interval_seconds=float(os.environ.get("DISCORD_POLL_INTERVAL_SECONDS", "5")),
        poll_attempts=int(os.environ.get("DISCORD_POLL_ATTEMPTS", "36")),
        request_timeout_seconds=float(os.environ.get("DISCORD_REQUEST_TIMEOUT_SECONDS", "30")),
        per_user_messages_per_minute=int(os.environ.get("DISCORD_USER_RATE_LIMIT", "10")),
    )
