"""Cầu nối mạng hẹp từ container Compose đến dịch vụ Ollama chỉ nghe trên loopback."""

import os

import httpx
from fastapi import FastAPI, HTTPException, Request, Response

UPSTREAM = os.getenv("OLLAMA_BRIDGE_UPSTREAM", "http://127.0.0.1:11434").rstrip("/")
MAX_REQUEST_BYTES = 2_000_000
ALLOWED_ROUTES = {
    ("GET", "api/tags"),
    ("GET", "api/version"),
    ("POST", "api/generate"),
}

app = FastAPI(
    title="Cầu nối Docker cho Ollama",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


async def forward(method: str, path: str, body: bytes) -> httpx.Response:
    async with httpx.AsyncClient(timeout=130) as client:
        return await client.request(
            method,
            f"{UPSTREAM}/{path}",
            content=body or None,
            headers={"content-type": "application/json"} if body else None,
        )


@app.api_route("/{path:path}", methods=["GET", "POST"])
async def proxy_ollama(path: str, request: Request) -> Response:
    normalized_path = path.strip("/")
    if (request.method, normalized_path) not in ALLOWED_ROUTES:
        raise HTTPException(404, "Cầu nối cục bộ không công khai đường dẫn Ollama này")
    body = await request.body()
    if len(body) > MAX_REQUEST_BYTES:
        raise HTTPException(413, "Yêu cầu Ollama vượt quá giới hạn dung lượng")
    try:
        upstream = await forward(request.method, normalized_path, body)
    except httpx.RequestError as exc:
        raise HTTPException(502, "Dịch vụ Ollama trên máy chủ hiện không sẵn sàng") from exc
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json").split(";", 1)[0],
    )
