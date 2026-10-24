"""Stable, non-sensitive errors shared by connection checks and real chat requests."""

import httpx

from app.services.object_storage import DocumentError


def chat_provider_error(
    provider: str, response: httpx.Response, *, model_request: bool = True
) -> DocumentError:
    try:
        payload = response.json()
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        error = error if isinstance(error, dict) else {}
    except ValueError:
        error = {}
    # Never return or log upstream text: providers sometimes echo credentials.
    code = str(error.get("code") or "").lower()
    kind = str(error.get("type") or "").lower()
    param = str(error.get("param") or "").lower()
    message = str(error.get("message") or "").lower()
    status = response.status_code
    if status == 401:
        result = "CHAT_API_KEY_INVALID", 422
    elif status == 403:
        result = "CHAT_API_ACCESS_DENIED", 422
    elif (provider == "deepseek" and status == 402) or code == "credit_balance_exhausted":
        result = "CHAT_CREDIT_EXHAUSTED", 402
    elif code in {"organization_spend_limit_exceeded", "project_spend_limit_exceeded"}:
        result = "CHAT_SPEND_LIMIT_REACHED", 402
    elif code == "organization_usage_limit_exceeded":
        result = "CHAT_USAGE_LIMIT_REACHED", 402
    elif code == "insufficient_quota" or kind == "insufficient_quota":
        result = "CHAT_QUOTA_EXCEEDED", 402
    elif status == 429:
        result = "CHAT_PROVIDER_RATE_LIMITED", 429
    elif model_request and (
        status == 404
        or code in {"model_not_found", "model_not_available", "invalid_model"}
        or (status in {400, 422} and "model" in message and "does not exist" in message)
    ):
        result = "CHAT_MODEL_UNAVAILABLE", 422
    elif (
        model_request
        and status in {400, 422}
        and (
            code in {"unsupported_model", "model_not_supported", "unsupported_parameter"}
            or param in {"model", "tools", "tool_choice", "parallel_tool_calls", "thinking"}
            or (
                "not support" in message
                and any(word in message for word in ("model", "tool", "responses", "chat"))
            )
        )
    ):
        result = "CHAT_MODEL_INCOMPATIBLE", 422
    elif status in {400, 422}:
        result = "CHAT_PROVIDER_REQUEST_REJECTED", 422
    elif status >= 500:
        result = "CHAT_PROVIDER_UNAVAILABLE", 503
    else:
        result = "CHAT_PROVIDER_FAILED", 502
    return DocumentError(result[0], "Chat provider request rejected", result[1])
