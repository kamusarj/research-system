"""Mã hóa bí mật của người dùng (token OAuth) trước khi ghi vào DB.

`CREDENTIALS_ENCRYPTION_KEY` là một hoặc nhiều khóa Fernet cách nhau bằng dấu phẩy: khóa đầu
dùng để mã hóa, mọi khóa đều dùng để giải mã, nên đổi khóa = thêm khóa mới lên đầu rồi gỡ khóa cũ
sau khi mọi bản ghi đã được ghi lại.
"""

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.core.config import settings


class VaultUnavailable(RuntimeError):
    """Chưa cấu hình khóa, hoặc bản mã không giải được bằng khóa hiện có."""


def _fernet() -> MultiFernet:
    secret = settings.credentials_encryption_key
    keys = [
        key.strip()
        for key in (secret.get_secret_value() if secret is not None else "").split(",")
        if key.strip()
    ]
    if not keys:
        raise VaultUnavailable("CREDENTIALS_ENCRYPTION_KEY is not configured")
    try:
        return MultiFernet([Fernet(key.encode()) for key in keys])
    except ValueError as exc:
        raise VaultUnavailable("CREDENTIALS_ENCRYPTION_KEY is not a valid Fernet key") from exc


def encrypt_json(payload: dict[str, Any]) -> str:
    return _fernet().encrypt(json.dumps(payload, separators=(",", ":")).encode()).decode()


def decrypt_json(token: str) -> dict[str, Any]:
    try:
        value = json.loads(_fernet().decrypt(token.encode()))
    except InvalidToken as exc:
        raise VaultUnavailable("Stored credentials cannot be decrypted") from exc
    if not isinstance(value, dict):
        raise VaultUnavailable("Stored credentials are malformed")
    return value


def primary_key_bytes() -> bytes:
    """Khóa mã hóa hiện hành, dùng làm gốc dẫn xuất định danh ổn định (không phải bí mật lộ ra)."""

    secret = settings.credentials_encryption_key
    first = (secret.get_secret_value() if secret is not None else "").split(",")[0].strip()
    if not first:
        raise VaultUnavailable("CREDENTIALS_ENCRYPTION_KEY is not configured")
    return first.encode()


def generate_key() -> str:
    return Fernet.generate_key().decode()
