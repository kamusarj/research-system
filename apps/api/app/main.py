import hmac
import logging
from contextlib import asynccontextmanager
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.router import api_router
from app.core.auth import AuthMiddleware
from app.core.config import settings
from app.core.localization import product_error_message
from app.core.observability import (
    OAuthCallbackLogFilter,
    ObservabilityMiddleware,
    configure_logging,
)
from app.core.request_guard import RequestGuardMiddleware
from app.core.runtime_controls import RuntimeControlsMiddleware
from app.services.neo4j_projection import GraphProjectionError
from app.services.object_storage import DocumentError
from app.services.search_projection import SearchProjectionError

logger = logging.getLogger(__name__)
# Nhật ký truy cập của uvicorn ghi cả query: không để mã OAuth của callback lọt vào log.
logging.getLogger("uvicorn.access").addFilter(OAuthCallbackLogFilter())

HTTP_ERROR_CODES = {
    401: "AUTH_REQUIRED",
    403: "ACCESS_DENIED",
    404: "SOURCE_NOT_FOUND",
    415: "UNSUPPORTED_CONTENT_TYPE",
    429: "RATE_LIMITED",
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.log_format == "json":
        configure_logging()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    GZipMiddleware,
    minimum_size=settings.http_gzip_minimum_size,
    compresslevel=settings.http_gzip_compresslevel,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time-Ms", "Server-Timing"],
)
app.add_middleware(RuntimeControlsMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(RequestGuardMiddleware)
app.add_middleware(ObservabilityMiddleware)
app.include_router(api_router, prefix="/api/v1")


OAUTH_CALLBACK_PARAMS = ("code", "state", "error", "client_id", "scope")


@app.get("/auth/callback", include_in_schema=False)
def chatgpt_plan_loopback_callback(request: Request) -> Response:
    """Chế độ cục bộ: OpenAI chỉ chuyển về loopback `127.0.0.1`, nơi trình duyệt không mang
    cookie đăng nhập của ứng dụng. Chuyển tiếp nguyên tham số sang trang web để trang đó hoàn tất
    trong đúng phiên của người đã bấm kết nối; tại đây không đổi mã lấy token."""

    origin = settings.chatgpt_plan_web_origin
    if not (settings.chatgpt_plan_enabled and settings.chatgpt_plan_local_mode and origin):
        raise HTTPException(status_code=404, detail="Không tìm thấy")
    params = {
        name: value[:4096]
        for name in OAUTH_CALLBACK_PARAMS
        if (value := request.query_params.get(name))
    }
    return RedirectResponse(
        f"{origin}/account/ai/callback?{urlencode(params)}",
        status_code=303,
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )


@app.get("/metrics", include_in_schema=False)
def metrics(request: Request) -> Response:
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Không tìm thấy")
    expected = settings.metrics_secret
    if expected is None:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "METRICS_NOT_CONFIGURED",
                    "message": "Chưa cấu hình xác thực cho dữ liệu giám sát",
                }
            },
        )
    authorization = request.headers.get("Authorization", "")
    scheme, separator, supplied = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not hmac.compare_digest(
        supplied, expected
    ):
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "code": "AUTH_REQUIRED",
                    "message": "Cần mã xác thực Bearer để xem dữ liệu giám sát",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Response(content=generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})


@app.exception_handler(DocumentError)
async def document_error(_: Request, exc: DocumentError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": product_error_message(exc.code, exc.status_code),
            }
        },
    )


@app.exception_handler(GraphProjectionError)
async def graph_projection_error(_: Request, exc: GraphProjectionError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": product_error_message(exc.code, exc.status_code),
            }
        },
    )


@app.exception_handler(SearchProjectionError)
async def search_projection_error(_: Request, exc: SearchProjectionError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": product_error_message(exc.code, exc.status_code),
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
    code = getattr(exc, "code", None) or HTTP_ERROR_CODES.get(exc.status_code, "INVALID_REQUEST")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": product_error_message(code, exc.status_code),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": (
                    "INVALID_URL"
                    if any(error.get("loc", [])[-1:] == ("url",) for error in exc.errors())
                    else "INVALID_REQUEST"
                ),
                "message": "Dữ liệu gửi lên chưa hợp lệ",
                "details": [
                    {
                        key: value
                        for key, value in error.items()
                        if key not in {"input", "ctx", "url", "msg"}
                    }
                    for error in exc.errors()
                ],
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_error(_: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled API error", exc_info=(type(exc), exc, exc.__traceback__))
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Máy chủ chưa thể hoàn tất yêu cầu này",
            }
        },
    )
