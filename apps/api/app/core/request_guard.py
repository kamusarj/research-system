"""Chặn DNS rebinding và request cross-site ở tầng API, kể cả khi tắt đăng nhập.

Khi `AUTH_MODE=disabled`, mọi request đều mang quyền chủ sở hữu cục bộ nên một trang độc hại
mà chủ sở hữu đang mở có thể gửi POST tới localhost (CSRF) hoặc trỏ tên miền của nó về
127.0.0.1 để đọc dữ liệu (DNS rebinding). Hai lớp kiểm tra:

- Host (và X-Forwarded-Host do proxy Next.js đặt, trình duyệt không giả được) phải thuộc danh
  sách tin cậy.
- Phương thức thay đổi dữ liệu từ trình duyệt phải là same-origin (`Sec-Fetch-Site`), hoặc
  `Origin` thuộc danh sách tin cậy với trình duyệt cũ. Client không phải trình duyệt (bot,
  script) không gửi các header này và vẫn đi tiếp tới lớp xác thực.
"""

from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import settings

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
SAME_ORIGIN_FETCH_SITES = frozenset({"same-origin", "none"})


def _hostname(authority: str) -> str:
    value = authority.split(",", 1)[0].strip()
    if not value:
        return ""
    return (urlsplit(f"//{value}").hostname or "").lower()


def _blocked(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content={"error": {"code": code, "message": message}}
    )


class RequestGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        trusted = settings.trusted_hosts
        if trusted is not None:
            for header in ("host", "x-forwarded-host"):
                value = request.headers.get(header)
                if value is not None and _hostname(value) not in trusted:
                    return _blocked(
                        400, "HOST_NOT_ALLOWED", "Tên máy chủ của yêu cầu không được chấp nhận"
                    )

        if request.method not in SAFE_METHODS:
            fetch_site = request.headers.get("sec-fetch-site")
            origin = request.headers.get("origin")
            if fetch_site is not None:
                allowed = fetch_site in SAME_ORIGIN_FETCH_SITES
            elif origin is not None:
                allowed = trusted is None or (
                    origin != "null" and _hostname(urlsplit(origin).netloc) in trusted
                )
            else:
                allowed = True
            if not allowed:
                return _blocked(
                    403, "CROSS_SITE_REQUEST_BLOCKED", "Yêu cầu từ trang web khác bị chặn"
                )

        return await call_next(request)
