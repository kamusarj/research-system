from typing import Any, Literal

SourceErrorCode = Literal[
    "INVALID_URL",
    "UNSUPPORTED_SOURCE",
    "SOURCE_NOT_FOUND",
    "AUTH_REQUIRED",
    "ACCESS_DENIED",
    "BOT_PROTECTED",
    "RATE_LIMITED",
    "FETCH_TIMEOUT",
    "FETCH_FAILED",
    "DNS_FAILED",
    "TLS_FAILED",
    "CONTENT_TOO_LARGE",
    "UNSUPPORTED_CONTENT_TYPE",
    "EXTRACTION_FAILED",
    "EMPTY_CONTENT",
    "JS_RENDER_REQUIRED",
    "CONSENT_WALL",
    "PAYWALL",
    "PDF_PARSE_FAILED",
    "PDF_SCANNED_OCR_DISABLED",
    "TRANSCRIPT_SOURCE_INVALID",
    "TRANSCRIPT_UNAVAILABLE",
    "AI_PROVIDER_NOT_CONFIGURED",
    "AI_PROVIDER_AUTH_FAILED",
    "AI_PROVIDER_RATE_LIMITED",
    "AI_PROVIDER_UNAVAILABLE",
    "AI_PROVIDER_ERROR",
    "AI_RESPONSE_INVALID",
    "STORAGE_UNAVAILABLE",
    "DATABASE_ERROR",
    "INTERNAL_ERROR",
]

# Codes a researcher can act on directly. The UI pairs each with a bilingual remediation
# hint; anything absent here is treated as an operator-facing failure.
USER_ACTIONABLE_CODES: frozenset[str] = frozenset(
    {
        "INVALID_URL",
        "UNSUPPORTED_SOURCE",
        "SOURCE_NOT_FOUND",
        "AUTH_REQUIRED",
        "ACCESS_DENIED",
        "BOT_PROTECTED",
        "CONTENT_TOO_LARGE",
        "UNSUPPORTED_CONTENT_TYPE",
        "EMPTY_CONTENT",
        "JS_RENDER_REQUIRED",
        "CONSENT_WALL",
        "PAYWALL",
        "PDF_SCANNED_OCR_DISABLED",
        "TRANSCRIPT_SOURCE_INVALID",
        "TRANSCRIPT_UNAVAILABLE",
    }
)

RETRYABLE_CODES: frozenset[str] = frozenset(
    {
        "RATE_LIMITED",
        "FETCH_TIMEOUT",
        "FETCH_FAILED",
        "DNS_FAILED",
        "AI_PROVIDER_RATE_LIMITED",
        "AI_PROVIDER_UNAVAILABLE",
        "STORAGE_UNAVAILABLE",
        "DATABASE_ERROR",
    }
)


class SourceError(Exception):
    """A safe, actionable source-processing failure.

    Internal exception details may be logged by the worker, but only ``message`` and
    structured, non-sensitive details are persisted for the UI.
    """

    def __init__(
        self,
        code: SourceErrorCode,
        message: str,
        *,
        retryable: bool = False,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.status_code = status_code
        self.details = details or {}

    @property
    def user_actionable(self) -> bool:
        return self.code in USER_ACTIONABLE_CODES
