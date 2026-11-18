"""Cầu nối hẹp từ Docker đến model trên loopback hoặc đầu SSH tunnel của máy chủ."""

import asyncio
import os
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Request, Response

PROTOCOL = os.getenv("LOCAL_MODEL_BRIDGE_PROTOCOL", "ollama")
UPSTREAM = os.getenv("LOCAL_MODEL_BRIDGE_UPSTREAM") or os.getenv(
    "OLLAMA_BRIDGE_UPSTREAM", "http://127.0.0.1:11434"
)
MAX_REQUEST_BYTES = 2_000_000
try:
    MAX_RESPONSE_BYTES = int(os.getenv("LOCAL_AI_MAX_RESPONSE_BYTES", "2000000"))
    WALL_TIMEOUT_SECONDS = float(os.getenv("LOCAL_MODEL_BRIDGE_TIMEOUT_SECONDS", "130"))
except ValueError:
    MAX_RESPONSE_BYTES, WALL_TIMEOUT_SECONDS = 0, 0
ALLOWED_ROUTES = {
    "ollama": {
        ("GET", "api/tags"),
        ("GET", "api/version"),
        ("POST", "api/generate"),
        ("POST", "api/chat"),
    },
    "openai_compatible": {
        ("GET", "v1/models"),
        ("POST", "v1/chat/completions"),
    },
}

app = FastAPI(
    title="Cầu nối Docker cho model cục bộ",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def upstream_origin() -> str:
    """Chỉ operator cấu hình origin; request không được thay host, đường dẫn hay credential."""

    try:
        if any(ord(char) <= 32 or ord(char) == 127 or char == "\\" for char in UPSTREAM):
            raise ValueError
        parsed = urlsplit(UPSTREAM)
        httpx.URL(UPSTREAM)
        valid_port = parsed.port is None or 1 <= parsed.port <= 65535
        valid = (
            parsed.scheme in {"http", "https"}
            and bool(parsed.hostname)
            and valid_port
            and parsed.username is None
            and parsed.password is None
            and not parsed.path.strip("/")
            and not parsed.query
            and not parsed.fragment
        )
    except (ValueError, httpx.InvalidURL):
        valid = False
    if not valid:
        raise HTTPException(503, "Địa chỉ máy chủ model chưa được cấu hình hợp lệ")
    return UPSTREAM.rstrip("/")


def authorization_header(request: Request) -> str | None:
    value = request.headers.get("authorization")
    if value is None:
        return None
    scheme, _, token = value.partition(" ")
    if (
        scheme.lower() != "bearer"
        or not token
        or len(value) > 8192
        or any(not 33 <= ord(char) <= 126 for char in token)
    ):
        raise HTTPException(400, "Thông tin xác thực model không hợp lệ")
    return value


async def bounded_body(request: Request) -> bytes:
    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            size = int(declared)
        except ValueError:
            raise HTTPException(400, "Kích thước yêu cầu model không hợp lệ") from None
        if size < 0:
            raise HTTPException(400, "Kích thước yêu cầu model không hợp lệ")
        if size > MAX_REQUEST_BYTES:
            raise HTTPException(413, "Yêu cầu model vượt quá giới hạn dung lượng")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_REQUEST_BYTES:
            raise HTTPException(413, "Yêu cầu model vượt quá giới hạn dung lượng")
        body.extend(chunk)
    return bytes(body)


async def forward(
    method: str, path: str, body: bytes, authorization: str | None = None
) -> httpx.Response:
    origin = upstream_origin()
    headers = {"accept": "application/json", "accept-encoding": "identity"}
    if body:
        headers["content-type"] = "application/json"
    if authorization:
        headers["authorization"] = authorization
    # Không dùng HTTP(S)_PROXY của môi trường và không đưa key sang redirect hoặc host khác.
    async with httpx.AsyncClient(
        timeout=WALL_TIMEOUT_SECONDS, follow_redirects=False, trust_env=False
    ) as client:
        async with client.stream(
            method, f"{origin}/{path}", content=body or None, headers=headers
        ) as upstream:
            if upstream.is_redirect:
                raise HTTPException(502, "Máy chủ model chuyển hướng ngoài kết nối đã cấu hình")
            if upstream.status_code >= 400:
                status = upstream.status_code
                if status not in {400, 401, 403, 404, 408, 413, 422, 429, 500, 502, 503, 504}:
                    status = 502
                raise HTTPException(status, "Máy chủ model từ chối hoặc chưa hoàn tất yêu cầu")
            if upstream.headers.get("content-encoding", "identity").lower() != "identity":
                raise HTTPException(502, "Máy chủ model trả về định dạng nén không được hỗ trợ")
            media_type = upstream.headers.get("content-type", "application/json").split(";", 1)[0]
            if media_type.strip().lower() != "application/json":
                raise HTTPException(502, "Máy chủ model chưa trả về phản hồi JSON hợp lệ")
            content = bytearray()
            async for chunk in upstream.aiter_bytes(chunk_size=min(65536, MAX_RESPONSE_BYTES + 1)):
                if len(content) + len(chunk) > MAX_RESPONSE_BYTES:
                    raise HTTPException(502, "Phản hồi model vượt quá giới hạn dung lượng")
                content.extend(chunk)
            return httpx.Response(upstream.status_code, content=bytes(content))


@app.api_route("/{path:path}", methods=["GET", "POST"])
async def proxy_ollama(path: str, request: Request) -> Response:
    routes = ALLOWED_ROUTES.get(PROTOCOL)
    if routes is None or MAX_RESPONSE_BYTES < 1 or not 0 < WALL_TIMEOUT_SECONDS <= 900:
        raise HTTPException(503, "Cầu nối model chưa được cấu hình hợp lệ")
    normalized_path = path.strip("/")
    if (request.method, normalized_path) not in routes:
        raise HTTPException(404, "Cầu nối cục bộ không công khai đường dẫn model này")
    try:
        async with asyncio.timeout(WALL_TIMEOUT_SECONDS):
            body = await bounded_body(request)
            authorization = authorization_header(request)
            upstream = await forward(request.method, normalized_path, body, authorization)
    except (httpx.TimeoutException, TimeoutError):
        raise HTTPException(504, "Máy chủ model chưa phản hồi trong thời gian cho phép") from None
    except httpx.HTTPError:
        raise HTTPException(502, "Dịch vụ model trên máy chủ hiện không sẵn sàng") from None
    return Response(
        content=upstream.content, status_code=upstream.status_code, media_type="application/json"
    )
