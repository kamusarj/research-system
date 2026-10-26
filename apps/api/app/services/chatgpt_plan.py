"""Gói ChatGPT của từng người dùng: Sign in with ChatGPT + ChatGPT plan usage.

Người dùng tự đăng nhập ChatGPT và cho phép ứng dụng dùng gói Plus/Pro của họ; lượt AI của
người đó gọi Responses API bằng access token của chính họ nên tính vào hạn mức gói của họ.
Hợp đồng theo https://developers.openai.com/siwc/ (bản preview 10/2026):

- OAuth Authorization Code + PKCE + OIDC; scope `offline_access resource.invoke
  chatgpt.tokens.use.direct`, `resource=https://api.openai.com/v1`.
- Không có client ID cấu hình = chế độ cục bộ: tự đăng ký bằng `dynamic_agent_client`, callback
  loopback `127.0.0.1` (chỉ dùng được từ trình duyệt trên máy chạy API). Bản chạy trên web cần
  client ID do OpenAI cấp qua form đối tác và callback đã đăng ký.
- Responses: bắt buộc `store=false`, `stream=true`; không gửi temperature/max_output_tokens.
- Token truy cập sống 1 giờ, refresh token 30 ngày và xoay vòng: làm mới phải tuần tự hóa.

Token chỉ lưu dạng mã hóa (`credentials_vault`) và không bao giờ đi vào log, URL hay trình duyệt.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import secrets
import time
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.identity import current_actor_id
from app.db import SessionLocal
from app.models import AIPlanAuthAttempt, AIPlanConnection, AuditEvent
from app.services.credentials_vault import (
    VaultUnavailable,
    decrypt_json,
    encrypt_json,
    primary_key_bytes,
)
from app.services.object_storage import DocumentError

logger = logging.getLogger(__name__)

PROVIDER_ID = "chatgpt_plan"
DYNAMIC_CLIENT = "dynamic_agent_client"
PLAN_SCOPE = "chatgpt.tokens.use.direct"
SCOPES = f"openid profile email offline_access resource.invoke {PLAN_SCOPE}"
USAGE_URL = "https://chatgpt.com/settings/usage"
ATTEMPT_TTL = timedelta(minutes=10)
REFRESH_MARGIN = timedelta(minutes=5)
MAX_MODELS = 50
UNUSABLE_REFRESH_CODES = frozenset(
    {
        "invalid_grant",
        "invalid_refresh_token",
        "token_expired",
        "refresh_token_expired",
        "refresh_token_invalidated",
        "refresh_token_reused",
    }
)
_CLIENT_ID = re.compile(r"^[A-Za-z0-9_.:-]{3,200}$")

# Điểm thay thế cho test: phiên DB riêng (token xoay vòng phải được commit ngay, độc lập với
# giao dịch của tác vụ đang gọi AI) và transport HTTP.
session_factory: Callable[[], Session] = SessionLocal
transport: httpx.BaseTransport | None = None


class ChatGPTPlanError(DocumentError):
    """Lỗi có mã ổn định; `retryable` = lỗi tạm thời, giữ nguyên thông tin đăng nhập."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        *,
        retryable: bool = False,
        request_id: str | None = None,
    ) -> None:
        super().__init__(code, message, status_code)
        self.retryable = retryable
        self.request_id = request_id


def utcnow() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    # SQLite trả về datetime không múi giờ; mọi giá trị lưu đều là UTC.
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _client(timeout: float = 20) -> httpx.Client:
    return httpx.Client(timeout=httpx.Timeout(timeout, connect=10), transport=transport)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def enabled() -> bool:
    return settings.chatgpt_plan_enabled


def _require_enabled() -> None:
    if not enabled():
        raise ChatGPTPlanError(
            "CHATGPT_PLAN_DISABLED", "Tính năng dùng gói ChatGPT chưa được bật", 503
        )


def host_id() -> str:
    """`ext_agent_host_id` ổn định cho máy chủ này: không chứa thông tin người dùng."""

    configured = settings.chatgpt_plan_host_id.strip()
    if configured:
        return configured
    digest = hmac.new(primary_key_bytes(), b"chatgpt-plan-agent-host", hashlib.sha256).digest()
    return f"urn:uuid:{uuid.UUID(bytes=digest[:16], version=4)}"


# --- Điểm cuối OAuth -------------------------------------------------------------------------

_discovery_cache: tuple[float, dict[str, Any]] | None = None


def discovery() -> dict[str, Any]:
    global _discovery_cache
    now = time.monotonic()
    if _discovery_cache and now - _discovery_cache[0] < 3600:
        return _discovery_cache[1]
    with _client(10) as client:
        response = client.get(f"{settings.chatgpt_plan_issuer}/.well-known/openid-configuration")
        response.raise_for_status()
        document = response.json()
    _discovery_cache = (now, document)
    return document


def _authorize_endpoint() -> str:
    if settings.chatgpt_plan_local_mode:
        # Luồng tự đăng ký cho ứng dụng cục bộ dùng đúng điểm cuối trong tài liệu OSS.
        return f"{settings.chatgpt_plan_issuer}/api/accounts/authorize"
    return str(discovery()["authorization_endpoint"])


def _token_endpoint() -> str:
    if settings.chatgpt_plan_local_mode:
        return f"{settings.chatgpt_plan_issuer}/api/accounts/oauth/token"
    return str(discovery()["token_endpoint"])


def _client_auth() -> tuple[str, str] | None:
    secret = settings.chatgpt_plan_client_secret
    if settings.chatgpt_plan_local_mode or secret is None:
        return None
    value = secret.get_secret_value().strip()
    return (settings.chatgpt_plan_client_id.strip(), value) if value else None


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge.rstrip(b"=").decode()


def _signing_key(id_token: str) -> Any:
    jwks = jwt.PyJWKClient(str(discovery()["jwks_uri"]), cache_keys=True, timeout=10)
    return jwks.get_signing_key_from_jwt(id_token).key


def validate_id_token(id_token: str, *, client_id: str, nonce: str) -> dict[str, Any]:
    try:
        claims = jwt.decode(
            id_token,
            _signing_key(id_token),
            algorithms=["RS256"],
            audience=client_id,
            issuer=settings.chatgpt_plan_issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            leeway=60,
        )
    except (jwt.PyJWTError, httpx.HTTPError, KeyError, ValueError) as exc:
        raise ChatGPTPlanError(
            "CHATGPT_PLAN_IDENTITY_INVALID", "Không xác minh được danh tính ChatGPT", 400
        ) from exc
    if not hmac.compare_digest(str(claims.get("nonce") or ""), nonce):
        raise ChatGPTPlanError(
            "CHATGPT_PLAN_IDENTITY_INVALID", "Không xác minh được danh tính ChatGPT", 400
        )
    return claims


# --- Kết nối của người dùng ------------------------------------------------------------------


def get_connection(db: Session, user_id: str) -> AIPlanConnection | None:
    return db.scalar(
        select(AIPlanConnection).where(
            AIPlanConnection.user_id == user_id, AIPlanConnection.provider == "chatgpt"
        )
    )


def connection_ready(user_id: str) -> bool:
    if not enabled():
        return False
    with session_factory() as db:
        connection = get_connection(db, user_id)
        return connection is not None and connection.status == "active"


def default_provider_for(db: Session | None, user_id: str | None = None) -> str | None:
    """Nhà cung cấp mặc định cho việc AI mới của người dùng (None = theo cấu hình máy chủ)."""

    if not enabled():
        return None
    user_id = user_id or current_actor_id()
    if db is None:
        with session_factory() as own:
            return default_provider_for(own, user_id)
    connection = get_connection(db, user_id)
    if connection is not None and connection.status == "active" and connection.use_by_default:
        return PROVIDER_ID
    return None


def ensure_owner_spends(provider_name: str | None, owner_id: str | None) -> None:
    """Gói ChatGPT của ai chỉ được tiêu cho việc chính người đó khởi chạy hoặc chạy lại."""

    if provider_name == PROVIDER_ID and owner_id != current_actor_id():
        raise ChatGPTPlanError(
            "CHATGPT_PLAN_OWNER_ONLY",
            "Việc này dùng gói ChatGPT của người tạo; chỉ người đó mới chạy lại được",
            403,
        )


def model_for(user_id: str) -> str:
    """Tên model hiển thị cho người dùng; không bao giờ ném lỗi."""

    fallback = settings.chatgpt_plan_default_model or "chatgpt-plan"
    if not enabled():
        return fallback
    try:
        with session_factory() as db:
            connection = get_connection(db, user_id)
            return (connection.model if connection else None) or fallback
    except Exception:  # noqa: BLE001 - chỉ dùng để hiển thị
        return fallback


def _audit(db: Session, connection: AIPlanConnection, action: str, **payload: Any) -> None:
    # Không ghi email, token hay mã OAuth vào nhật ký kiểm toán.
    db.add(
        AuditEvent(
            entity_type="ai_plan_connection",
            entity_id=connection.id,
            action=action,
            actor=connection.user_id,
            payload=payload,
        )
    )


def start_authorization(db: Session, user_id: str) -> str:
    _require_enabled()
    now = utcnow()
    # Dọn lượt hết hạn, và lượt cũ chưa dùng của chính người này: chỉ lượt mới nhất còn hiệu lực.
    db.execute(
        delete(AIPlanAuthAttempt)
        .where(
            (AIPlanAuthAttempt.expires_at < now)
            | ((AIPlanAuthAttempt.user_id == user_id) & AIPlanAuthAttempt.consumed_at.is_(None))
        )
        .execution_options(synchronize_session=False)
    )
    connection = get_connection(db, user_id)
    configured_client = settings.chatgpt_plan_client_id.strip()
    client_id = configured_client or (connection.client_id if connection else DYNAMIC_CLIENT)
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier, challenge = _pkce_pair()
    redirect_uri = settings.chatgpt_plan_callback
    db.add(
        AIPlanAuthAttempt(
            state_hash=_hash(state),
            user_id=user_id,
            client_id=client_id,
            redirect_uri=redirect_uri,
            encrypted_secret=encrypt_json({"verifier": verifier, "nonce": nonce}),
            expires_at=now + ATTEMPT_TTL,
        )
    )
    params: dict[str, str] = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "resource": settings.chatgpt_plan_api_base,
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if settings.chatgpt_plan_local_mode:
        params["ext_agent_host_id"] = host_id()
        if client_id == DYNAMIC_CLIENT:
            params["agent_name_hint"] = settings.chatgpt_plan_agent_name
    if connection is not None:
        if connection.email:
            params["login_hint"] = connection.email
        if connection.status == "plan_disabled":
            # Người dùng muốn bật lại sau khi đã từ chối: hỏi lại sự đồng ý một lần.
            params["prompt"] = "consent"
        id_token = _stored_tokens(connection).get("id_token")
        if id_token and connection.status != "signed_out":
            params["id_token_hint"] = id_token
    db.commit()
    return f"{_authorize_endpoint()}?{urlencode(params)}"


def _consume_attempt(db: Session, user_id: str, state: str) -> AIPlanAuthAttempt:
    attempt = db.scalar(
        select(AIPlanAuthAttempt)
        .where(AIPlanAuthAttempt.state_hash == _hash(state))
        .with_for_update()
    )
    now = utcnow()
    expires_at = _aware(attempt.expires_at) if attempt else None
    if (
        attempt is None
        or attempt.consumed_at is not None
        or expires_at is None
        or expires_at < now
        # Mã chỉ hoàn tất được trong phiên của chính người đã bắt đầu: chặn việc lừa người khác
        # bấm link để gắn gói ChatGPT của họ vào tài khoản kẻ tấn công.
        or not hmac.compare_digest(attempt.user_id, user_id)
    ):
        raise ChatGPTPlanError(
            "CHATGPT_PLAN_STATE_INVALID",
            "Phiên kết nối đã hết hạn hoặc không hợp lệ; hãy thử kết nối lại",
            400,
        )
    attempt.consumed_at = now
    db.flush()
    return attempt


def _token_request(form: dict[str, str]) -> httpx.Response:
    with _client() as client:
        return client.post(
            _token_endpoint(),
            data=form,
            auth=_client_auth(),
            headers={"Accept": "application/json"},
        )


def _oauth_error_code(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("code") or "")
    return str(error or payload.get("code") or "")


def _expiry(token_response: dict[str, Any], now: datetime) -> datetime:
    try:
        seconds = int(token_response.get("expires_in") or 3600)
    except (TypeError, ValueError):
        seconds = 3600
    return now + timedelta(seconds=max(60, min(seconds, 86_400)))


def _earliest_refresh(value: Any, now: datetime) -> datetime | None:
    if isinstance(value, int | float) and value > 0:
        # Mốc Unix nếu đủ lớn, ngược lại là số giây kể từ bây giờ.
        if value > 1_000_000_000:
            return datetime.fromtimestamp(value, UTC)
        return now + timedelta(seconds=value)
    if isinstance(value, str) and value:
        try:
            return _aware(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except ValueError:
            return None
    return None


def _stored_tokens(connection: AIPlanConnection, *, strict: bool = False) -> dict[str, Any]:
    if not connection.encrypted_tokens:
        return {}
    try:
        return decrypt_json(connection.encrypted_tokens)
    except VaultUnavailable as exc:
        if strict:
            # Khóa máy chủ sai/thiếu: lỗi vận hành, không phải lỗi của người dùng; giữ nguyên
            # trạng thái kết nối để sửa khóa xong là dùng lại được.
            raise ChatGPTPlanError(
                "CHATGPT_PLAN_VAULT_UNAVAILABLE",
                "Máy chủ không giải mã được thông tin kết nối ChatGPT",
                503,
                retryable=True,
            ) from exc
        return {}


def _model_catalog(access_token: str) -> list[dict[str, str]]:
    try:
        with _client(15) as client:
            response = client.get(
                f"{settings.chatgpt_plan_api_base}/models",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError):
        return []
    models = payload.get("models") if isinstance(payload, dict) else None
    catalog: list[dict[str, str]] = []
    for item in models if isinstance(models, list) else []:
        if not isinstance(item, dict) or item.get("visibility") != "list":
            continue
        slug = str(item.get("slug") or "").strip()
        if slug and len(slug) <= 200:
            catalog.append({"slug": slug, "display_name": str(item.get("display_name") or slug)})
        if len(catalog) >= MAX_MODELS:
            break
    return catalog


def _choose_model(current: str | None, catalog: list[dict[str, str]]) -> str | None:
    slugs = [item["slug"] for item in catalog]
    for candidate in (current, settings.chatgpt_plan_default_model.strip() or None):
        if candidate and (not slugs or candidate in slugs):
            return candidate
    return slugs[0] if slugs else current


def complete_authorization(
    db: Session,
    user_id: str,
    *,
    state: str,
    code: str | None,
    callback_client_id: str | None = None,
    error: str | None = None,
) -> AIPlanConnection:
    _require_enabled()
    attempt = _consume_attempt(db, user_id, state)
    db.commit()  # Đánh dấu đã dùng trước khi gọi ra ngoài: mã không bao giờ được đổi hai lần.
    if error:
        connection = get_connection(db, user_id)
        if error == "access_denied" and connection is not None and connection.status != "active":
            connection.status = "plan_disabled"
            db.commit()
        raise ChatGPTPlanError(
            "CHATGPT_PLAN_CONSENT_DECLINED"
            if error == "access_denied"
            else "CHATGPT_PLAN_AUTH_FAILED",
            "Bạn chưa cho phép ứng dụng dùng gói ChatGPT"
            if error == "access_denied"
            else "ChatGPT không hoàn tất đăng nhập",
            400,
        )
    if not code:
        raise ChatGPTPlanError("CHATGPT_PLAN_AUTH_FAILED", "Thiếu mã ủy quyền từ ChatGPT", 400)

    client_id = attempt.client_id
    if client_id == DYNAMIC_CLIENT:
        # Đăng ký lần đầu: callback mang client ID vừa cấp; thiếu nghĩa là đăng ký dở dang.
        if (
            not callback_client_id
            or not _CLIENT_ID.fullmatch(callback_client_id)
            or (callback_client_id == DYNAMIC_CLIENT)
        ):
            raise ChatGPTPlanError(
                "CHATGPT_PLAN_AUTH_FAILED", "ChatGPT không trả về đăng ký ứng dụng", 400
            )
        client_id = callback_client_id
    elif callback_client_id and callback_client_id != client_id:
        raise ChatGPTPlanError(
            "CHATGPT_PLAN_AUTH_FAILED", "Đăng ký ứng dụng trả về không khớp", 400
        )

    secret = decrypt_json(attempt.encrypted_secret)
    try:
        response = _token_request(
            {
                "grant_type": "authorization_code",
                "client_id": client_id,
                "code": code,
                "code_verifier": str(secret["verifier"]),
                "redirect_uri": attempt.redirect_uri,
                "resource": settings.chatgpt_plan_api_base,
            }
        )
    except httpx.HTTPError as exc:
        raise ChatGPTPlanError(
            "CHATGPT_PLAN_UNAVAILABLE", "Không kết nối được tới ChatGPT", 503, retryable=True
        ) from exc
    if response.status_code != 200:
        logger.warning(
            "ChatGPT plan code exchange rejected",
            extra={
                "action": "chatgpt_plan.exchange.rejected",
                "status_code": response.status_code,
                "error_code": _oauth_error_code(response)[:80],
            },
        )
        raise ChatGPTPlanError(
            "CHATGPT_PLAN_AUTH_FAILED", "ChatGPT từ chối mã ủy quyền; hãy kết nối lại", 400
        )
    try:
        tokens = response.json()
        access_token = str(tokens["access_token"])
        id_token = str(tokens["id_token"])
    except (ValueError, KeyError, TypeError) as exc:
        raise ChatGPTPlanError(
            "CHATGPT_PLAN_AUTH_FAILED", "ChatGPT trả về phản hồi đăng nhập không hợp lệ", 502
        ) from exc
    claims = validate_id_token(id_token, client_id=client_id, nonce=str(secret["nonce"]))
    granted = sorted(set(str(tokens.get("scope") or "").split()))

    now = utcnow()
    connection = get_connection(db, user_id)
    if connection is not None and connection.subject and connection.subject != str(claims["sub"]):
        # Đăng ký cũ gắn với tài khoản/workspace khác: không ghi đè token của đăng ký đó, và thu
        # hồi ngay phiên vừa cấp cho tài khoản kia để không để lại quyền mồ côi.
        if tokens.get("refresh_token"):
            _revoke(str(tokens["refresh_token"]), client_id)
        raise ChatGPTPlanError(
            "CHATGPT_PLAN_ACCOUNT_MISMATCH",
            "Đây là tài khoản ChatGPT khác với tài khoản đã kết nối; hãy xóa kết nối cũ trước",
            409,
        )
    if connection is None:
        connection = AIPlanConnection(
            user_id=user_id,
            provider="chatgpt",
            issuer=settings.chatgpt_plan_issuer,
            subject=str(claims["sub"]),
            client_id=client_id,
            models_json=[],
            scopes=[],
        )
        db.add(connection)
    # Client ID và token luôn được thay cùng nhau (ví dụ khi chuyển từ cục bộ sang client đối tác).
    connection.client_id = client_id
    plan_allowed = PLAN_SCOPE in granted
    catalog = _model_catalog(access_token) if plan_allowed else []
    connection.email = str(claims.get("email") or "")[:320] or None
    connection.scopes = granted
    connection.models_json = catalog or list(connection.models_json or [])
    connection.model = _choose_model(connection.model, connection.models_json)
    connection.encrypted_tokens = encrypt_json(
        {
            "access_token": access_token,
            "refresh_token": str(tokens.get("refresh_token") or ""),
            "id_token": id_token,
        }
    )
    connection.access_expires_at = _expiry(tokens, now)
    connection.earliest_refresh_at = _earliest_refresh(tokens.get("earliest_refresh_at"), now)
    connection.status = "active" if plan_allowed else "plan_disabled"
    connection.last_error_code = None if plan_allowed else "CHATGPT_PLAN_SCOPE_MISSING"
    connection.connected_at = now
    db.flush()
    _audit(db, connection, "ai_plan.connected", plan_usage=plan_allowed, scopes=granted)
    db.commit()
    return connection


def set_preferences(
    db: Session, user_id: str, *, model: str | None = None, use_by_default: bool | None = None
) -> AIPlanConnection:
    _require_enabled()
    connection = get_connection(db, user_id)
    if connection is None:
        raise ChatGPTPlanError("CHATGPT_PLAN_NOT_CONNECTED", "Bạn chưa kết nối gói ChatGPT", 409)
    if model is not None:
        slugs = {item.get("slug") for item in connection.models_json or []}
        if model not in slugs:
            raise ChatGPTPlanError(
                "CHATGPT_PLAN_MODEL_UNAVAILABLE", "Model này không có trong gói của bạn", 422
            )
        connection.model = model
    if use_by_default is not None:
        connection.use_by_default = use_by_default
    db.commit()
    return connection


def _revoke(refresh_token: str, client_id: str) -> bool:
    """Thu hồi phiên gia hạn; True khi OpenAI xác nhận (HTTP 200, kể cả token đã vô hiệu)."""

    for attempt in range(3):
        if attempt:
            time.sleep(0.5 * attempt)
        try:
            with _client(10) as client:
                response = client.post(
                    str(discovery()["revocation_endpoint"]),
                    data={
                        "token": refresh_token,
                        "token_type_hint": "refresh_token",
                        "client_id": client_id,
                    },
                    auth=_client_auth(),
                )
        except (httpx.HTTPError, KeyError, ValueError):
            continue
        if response.status_code == 200:
            return True
        if response.status_code < 500:
            return False
    return False


def disconnect(db: Session, user_id: str, *, forget: bool = False) -> bool:
    """Thu hồi phiên gia hạn tại OpenAI rồi xóa token. Trả về True nếu OpenAI xác nhận thu hồi."""

    connection = get_connection(db, user_id)
    if connection is None:
        return True
    try:
        refresh_token = _stored_tokens(connection, strict=True).get("refresh_token")
    except ChatGPTPlanError:
        refresh_token = None
        revoked = False  # Không đọc được token thì không thể xác nhận đã thu hồi.
    else:
        revoked = not refresh_token
    if refresh_token and enabled():
        revoked = _revoke(str(refresh_token), connection.client_id)
    _audit(db, connection, "ai_plan.disconnected", remote_revoked=revoked, forget=forget)
    if forget:
        db.delete(connection)
    else:
        # Giữ client ID + danh tính để lần sau đăng nhập lại đúng đăng ký đó.
        connection.encrypted_tokens = None
        connection.access_expires_at = None
        connection.earliest_refresh_at = None
        connection.status = "signed_out"
    db.commit()
    return revoked


# --- Token cho lượt gọi AI -------------------------------------------------------------------


def _mark(db: Session, connection: AIPlanConnection, status: str, code: str) -> None:
    connection.status = status
    connection.last_error_code = code
    db.commit()


def _refresh(db: Session, connection: AIPlanConnection) -> dict[str, Any]:
    tokens = _stored_tokens(connection, strict=True)
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        _mark(db, connection, "reauth_required", "CHATGPT_PLAN_REAUTH_REQUIRED")
        raise _reauth_error()
    try:
        response = _token_request(
            {
                "grant_type": "refresh_token",
                "client_id": connection.client_id,
                "refresh_token": str(refresh_token),
                "resource": settings.chatgpt_plan_api_base,
            }
        )
    except httpx.HTTPError as exc:
        raise ChatGPTPlanError(
            "CHATGPT_PLAN_UNAVAILABLE",
            "Không làm mới được phiên ChatGPT; sẽ thử lại",
            503,
            retryable=True,
        ) from exc
    if response.status_code != 200:
        code = _oauth_error_code(response)
        if response.status_code >= 500:
            raise ChatGPTPlanError(
                "CHATGPT_PLAN_UNAVAILABLE",
                "Không làm mới được phiên ChatGPT; sẽ thử lại",
                503,
                retryable=True,
            )
        if code in UNUSABLE_REFRESH_CODES or code == "invalid_client":
            tokens.pop("access_token", None)
            tokens.pop("refresh_token", None)
            connection.encrypted_tokens = encrypt_json(tokens)
            _mark(db, connection, "reauth_required", "CHATGPT_PLAN_REAUTH_REQUIRED")
            raise _reauth_error()
        logger.warning(
            "ChatGPT plan refresh rejected",
            extra={
                "action": "chatgpt_plan.refresh.rejected",
                "status_code": response.status_code,
                "error_code": code[:80],
            },
        )
        raise ChatGPTPlanError("CHATGPT_PLAN_FAILED", "ChatGPT từ chối làm mới phiên", 502)
    try:
        payload = response.json()
        new_access = str(payload["access_token"])
    except (ValueError, KeyError, TypeError) as exc:
        raise ChatGPTPlanError(
            "CHATGPT_PLAN_FAILED", "ChatGPT trả về phản hồi làm mới không hợp lệ", 502
        ) from exc
    now = utcnow()
    tokens["access_token"] = new_access
    if payload.get("refresh_token"):
        tokens["refresh_token"] = str(payload["refresh_token"])
    if payload.get("id_token"):
        tokens["id_token"] = str(payload["id_token"])
    # Thay access token, hạn dùng, scope và refresh token xoay vòng cùng một lần ghi.
    connection.encrypted_tokens = encrypt_json(tokens)
    connection.access_expires_at = _expiry(payload, now)
    connection.earliest_refresh_at = _earliest_refresh(payload.get("earliest_refresh_at"), now)
    if payload.get("scope"):
        connection.scopes = sorted(set(str(payload["scope"]).split()))
    db.commit()
    return tokens


def _reauth_error() -> ChatGPTPlanError:
    return ChatGPTPlanError(
        "CHATGPT_PLAN_REAUTH_REQUIRED",
        "Phiên ChatGPT đã hết hạn; hãy kết nối lại trong trang Tài khoản",
        409,
    )


def _needs_refresh(connection: AIPlanConnection, now: datetime) -> bool:
    expires_at = _aware(connection.access_expires_at)
    if expires_at is None or expires_at - REFRESH_MARGIN > now:
        return False
    earliest = _aware(connection.earliest_refresh_at)
    return expires_at <= now or earliest is None or earliest <= now


def access_token(user_id: str, *, force_refresh: bool = False) -> tuple[str, str]:
    """Access token còn hạn và model đã chọn của người dùng; làm mới nếu sắp hết hạn."""

    _require_enabled()
    with session_factory() as db:
        connection = get_connection(db, user_id)
        if connection is None or connection.status == "signed_out":
            raise ChatGPTPlanError(
                "CHATGPT_PLAN_NOT_CONNECTED",
                "Bạn chưa kết nối gói ChatGPT; vào trang Tài khoản để kết nối",
                409,
            )
        if connection.status == "plan_disabled":
            raise ChatGPTPlanError(
                "CHATGPT_PLAN_SCOPE_MISSING",
                "Bạn chưa cho phép ứng dụng dùng gói ChatGPT; hãy kết nối lại",
                409,
            )
        if connection.status == "reauth_required":
            raise _reauth_error()
        tokens = _stored_tokens(connection, strict=True)
        if force_refresh or _needs_refresh(connection, utcnow()) or not tokens.get("access_token"):
            # Khóa hàng (đọc lại) để hai lượt song song không cùng xoay một refresh token.
            db.refresh(connection, with_for_update=True)
            tokens = _stored_tokens(connection, strict=True)
            if (
                force_refresh
                or _needs_refresh(connection, utcnow())
                or not tokens.get("access_token")
            ):
                tokens = _refresh(db, connection)
        access = str(tokens["access_token"])
        model = connection.model
        if not model:
            # Danh mục model chưa lấy được lúc kết nối: thử lại một lần bằng token hiện có.
            catalog = _model_catalog(access)
            if catalog:
                connection.models_json = catalog
                connection.model = _choose_model(None, catalog)
                db.commit()
            model = connection.model or settings.chatgpt_plan_default_model
        if not model:
            raise ChatGPTPlanError(
                "CHATGPT_PLAN_MODEL_UNAVAILABLE",
                "Chưa lấy được danh sách model của gói ChatGPT",
                503,
                retryable=True,
            )
        return access, model


def _record_success(user_id: str) -> None:
    with session_factory() as db:
        connection = get_connection(db, user_id)
        if connection is not None:
            connection.last_used_at = utcnow()
            connection.last_error_code = None
            db.commit()


def _record_failure(user_id: str, status: str | None, code: str) -> None:
    with session_factory() as db:
        connection = get_connection(db, user_id)
        if connection is None:
            return
        if status:
            connection.status = status
        connection.last_error_code = code
        db.commit()


# --- Responses API -----------------------------------------------------------------------------


def _sse_events(lines: Iterator[str]) -> Iterator[dict[str, Any]]:
    data: list[str] = []
    for line in lines:
        if line == "":
            if data:
                raw = "\n".join(data)
                data = []
                if raw.strip() == "[DONE]":
                    return
                try:
                    event = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(event, dict):
                    yield event
            continue
        if line.startswith("data:"):
            data.append(line[5:].lstrip())
    if data:
        try:
            event = json.loads("\n".join(data))
        except ValueError:
            return
        if isinstance(event, dict):
            yield event


RESPONSE_ERRORS: dict[str, tuple[str, str, int, str | None, bool]] = {
    # mã OpenAI: (mã của ta, thông báo, HTTP, trạng thái kết nối mới, thử lại được)
    "subscription_sharing_usage_limit_exceeded": (
        "CHATGPT_PLAN_LIMIT_REACHED",
        "Đã chạm hạn mức gói ChatGPT (hoặc giới hạn riêng cho ứng dụng này)",
        429,
        None,
        False,
    ),
    "subscription_sharing_user_not_eligible": (
        "CHATGPT_PLAN_NOT_ELIGIBLE",
        "Tài khoản hoặc workspace ChatGPT này không được dùng gói cho ứng dụng",
        403,
        None,
        False,
    ),
    "subscription_sharing_usage_unavailable": (
        "CHATGPT_PLAN_UNAVAILABLE",
        "ChatGPT tạm thời chưa kiểm tra được hạn mức; sẽ thử lại",
        503,
        None,
        True,
    ),
    "subscription_sharing_user_unavailable": (
        "CHATGPT_PLAN_UNAVAILABLE",
        "ChatGPT tạm thời không phản hồi; sẽ thử lại",
        503,
        None,
        True,
    ),
    "subscription_sharing_unsupported_capability": (
        "CHATGPT_PLAN_UNSUPPORTED",
        "Gói ChatGPT không hỗ trợ yêu cầu này (model hoặc tính năng)",
        400,
        None,
        False,
    ),
    "subscription_sharing_route_not_supported": (
        "CHATGPT_PLAN_UNSUPPORTED",
        "Gói ChatGPT không hỗ trợ yêu cầu này",
        400,
        None,
        False,
    ),
    "subscription_sharing_invalid_user": (
        "CHATGPT_PLAN_REAUTH_REQUIRED",
        "Phiên ChatGPT không còn hợp lệ; hãy kết nối lại",
        409,
        "reauth_required",
        False,
    ),
    "chatpass_v2_scope_not_authorized": (
        "CHATGPT_PLAN_SCOPE_MISSING",
        "Quyền dùng gói ChatGPT chưa được cấp; hãy kết nối lại",
        409,
        "plan_disabled",
        False,
    ),
    "chatpass_v2_invalid_authorization_context": (
        "CHATGPT_PLAN_SCOPE_MISSING",
        "Quyền dùng gói ChatGPT chưa được cấp; hãy kết nối lại",
        409,
        "plan_disabled",
        False,
    ),
}


class _Upstream(Exception):
    """Lỗi thô từ Responses API trước khi quyết định thử lại hay báo cho người dùng."""

    def __init__(self, code: str | None, http_status: int, request_id: str | None) -> None:
        super().__init__(code or str(http_status))
        self.code = code
        self.http_status = http_status
        self.request_id = request_id

    @property
    def unauthorized(self) -> bool:
        return self.code == "subscription_sharing_invalid_user" or (
            self.code is None and self.http_status == 401
        )


def _plan_error(
    user_id: str, code: str | None, http_status: int, request_id: str | None
) -> ChatGPTPlanError:
    mapped = RESPONSE_ERRORS.get(code or "")
    if mapped:
        our_code, message, status_code, new_status, retryable = mapped
    elif http_status == 401:
        our_code, message, status_code, new_status, retryable = (
            "CHATGPT_PLAN_REAUTH_REQUIRED",
            "ChatGPT không chấp nhận quyền của ứng dụng; hãy kết nối lại",
            409,
            "reauth_required",
            False,
        )
    elif http_status == 403:
        our_code, message, status_code, new_status, retryable = (
            "CHATGPT_PLAN_NOT_ELIGIBLE",
            "ChatGPT chặn yêu cầu (khu vực hoặc chính sách)",
            403,
            None,
            False,
        )
    elif http_status == 429:
        our_code, message, status_code, new_status, retryable = (
            "CHATGPT_PLAN_LIMIT_REACHED",
            "Đã chạm hạn mức gói ChatGPT",
            429,
            None,
            False,
        )
    elif http_status >= 500:
        our_code, message, status_code, new_status, retryable = (
            "CHATGPT_PLAN_UNAVAILABLE",
            "ChatGPT tạm thời không phản hồi; sẽ thử lại",
            503,
            None,
            True,
        )
    else:
        our_code, message, status_code, new_status, retryable = (
            "CHATGPT_PLAN_FAILED",
            "ChatGPT không hoàn tất yêu cầu",
            502,
            None,
            False,
        )
    if not retryable:
        _record_failure(user_id, new_status, our_code)
    logger.warning(
        "ChatGPT plan request failed",
        extra={
            "action": "chatgpt_plan.request.failed",
            "error_code": our_code,
            "upstream_code": (code or "")[:80],
            "status_code": http_status,
            "request_id": request_id,
        },
    )
    return ChatGPTPlanError(
        our_code, message, status_code, retryable=retryable, request_id=request_id
    )


def _admission_code(response: httpx.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    error = payload.get("error") if isinstance(payload, dict) else None
    return str(error.get("code")) if isinstance(error, dict) and error.get("code") else None


def _stream(access: str, body: dict[str, Any]) -> tuple[dict[str, Any], str, str | None]:
    deltas: list[str] = []
    with _client(settings.ai_request_timeout) as client:
        with client.stream(
            "POST",
            f"{settings.chatgpt_plan_api_base}/responses",
            headers={
                "Authorization": f"Bearer {access}",
                "Accept": "text/event-stream",
                "Content-Type": "application/json",
            },
            json=body,
        ) as response:
            request_id = response.headers.get("x-request-id")
            if response.status_code >= 400:
                response.read()
                raise _Upstream(_admission_code(response), response.status_code, request_id)
            for event in _sse_events(response.iter_lines()):
                kind = event.get("type")
                if kind == "response.output_text.delta":
                    deltas.append(str(event.get("delta") or ""))
                elif kind == "response.completed":
                    final = event.get("response")
                    return (final if isinstance(final, dict) else {}), "".join(deltas), request_id
                elif kind in {"response.failed", "error"}:
                    error = (
                        (event.get("response") or {}).get("error")
                        if kind == "response.failed"
                        else event.get("error") or event
                    )
                    code = error.get("code") if isinstance(error, dict) else None
                    raise _Upstream(str(code) if code else None, 400, request_id)
                elif kind == "response.incomplete":
                    raise ChatGPTPlanError(
                        "CHATGPT_PLAN_INCOMPLETE",
                        "ChatGPT dừng giữa chừng trước khi trả lời xong",
                        502,
                        request_id=request_id,
                    )
    raise ChatGPTPlanError(
        "CHATGPT_PLAN_INCOMPLETE",
        "Luồng phản hồi kết thúc trước khi hoàn tất",
        502,
        retryable=True,
    )


def _output_text(final: dict[str, Any], streamed: str) -> str:
    text = final.get("output_text")
    if isinstance(text, str) and text:
        return text
    for item in final.get("output") or []:
        for part in (item or {}).get("content") or []:
            if isinstance(part, dict) and part.get("type") == "output_text" and part.get("text"):
                return str(part["text"])
    return streamed


def plan_complete(
    user_id: str,
    *,
    prompt: str,
    schema: dict[str, Any],
    system: str,
    schema_name: str = "result",
) -> dict[str, Any]:
    """Một lượt JSON có cấu trúc tính vào gói ChatGPT của `user_id`.

    Trả về cùng dạng với cầu nối CLI: `{"output": dict, "usage": {...}, "request_id": ...}`.
    """

    access, model = access_token(user_id)
    body: dict[str, Any] = {
        "model": model,
        "instructions": system,
        "input": [{"role": "user", "content": prompt}],
        "text": {
            "format": {
                "type": "json_schema",
                "name": re.sub(r"[^a-zA-Z0-9_-]", "_", schema_name)[:64] or "result",
                # Không strict: schema Pydantic có trường tùy chọn mà chế độ strict từ chối;
                # kết quả vẫn được kiểm tra lại bằng Pydantic phía máy chủ.
                "strict": False,
                "schema": schema,
            }
        },
        "store": False,
        "stream": True,
    }
    if settings.chatgpt_plan_reasoning_effort:
        body["reasoning"] = {"effort": settings.chatgpt_plan_reasoning_effort}
    try:
        try:
            final, streamed, request_id = _stream(access, body)
        except _Upstream as exc:
            if not exc.unauthorized:
                raise
            # Access token có thể vừa bị vô hiệu phía OpenAI: làm mới một lần rồi thử lại.
            access, _ = access_token(user_id, force_refresh=True)
            final, streamed, request_id = _stream(access, body)
    except _Upstream as exc:
        raise _plan_error(user_id, exc.code, exc.http_status, exc.request_id) from None
    except httpx.TimeoutException as exc:
        raise ChatGPTPlanError(
            "CHATGPT_PLAN_TIMEOUT", "ChatGPT trả lời quá lâu", 504, retryable=True
        ) from exc
    except httpx.HTTPError as exc:
        raise ChatGPTPlanError(
            "CHATGPT_PLAN_UNAVAILABLE", "Không kết nối được tới ChatGPT", 503, retryable=True
        ) from exc
    text = _output_text(final, streamed)
    try:
        output = json.loads(text)
    except ValueError as exc:
        raise ValueError("ChatGPT plan response was not valid JSON") from exc
    if not isinstance(output, dict):
        raise ValueError("ChatGPT plan response was not a JSON object")
    _record_success(user_id)
    return {"output": output, "usage": final.get("usage") or {}, "request_id": request_id}


def actor_or_current(user_id: str | None) -> str:
    return user_id or current_actor_id()
