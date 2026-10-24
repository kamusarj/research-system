"""Nguồn tìm kiếm (SearXNG tự host, kho nội bộ), bộ nhớ đệm có hạn dùng và khử trùng nguồn."""

import hashlib
import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Protocol
from urllib.parse import urlsplit

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ResearchItem, ResearchWebCache, utcnow
from app.services.sources import normalize_url

logger = logging.getLogger("research-agent.search")

SEARXNG_MAX_RESPONSE_BYTES = 1_000_000
_WORD = re.compile(r"\w+", re.UNICODE)


@dataclass
class SearchHit:
    url: str
    title: str
    snippet: str
    provider: str
    rank: int
    research_item_id: str | None = None
    content: str = ""  # nguồn nội bộ đã có sẵn văn bản, không cần tải
    extra: dict[str, Any] = field(default_factory=dict)


class SearchProvider(Protocol):
    name: str

    def search(self, query: str, *, limit: int) -> list[SearchHit]: ...


class SearxngSearchProvider:
    """Gọi API JSON của SearXNG trong mạng nội bộ Compose.

    Không đi qua `fetch_public` (vốn chặn đúng địa chỉ nội bộ); URL cố định theo cấu hình, không
    theo chuyển hướng, giới hạn kích thước phản hồi. URL kết quả chỉ được tải qua `fetch_url`.
    """

    name = "searxng"

    def __init__(self, base_url: str | None = None, client: httpx.Client | None = None):
        self.base_url = (base_url or settings.searxng_url).rstrip("/")
        self.client = client or httpx.Client(
            timeout=settings.searxng_timeout_seconds, follow_redirects=False
        )

    def search(self, query: str, *, limit: int) -> list[SearchHit]:
        params = {"q": query, "format": "json", "safesearch": "1"}
        if settings.searxng_engines:
            params["engines"] = settings.searxng_engines
        with self.client.stream("GET", f"{self.base_url}/search", params=params) as response:
            response.raise_for_status()
            body = b""
            for chunk in response.iter_bytes():
                body += chunk
                if len(body) > SEARXNG_MAX_RESPONSE_BYTES:
                    raise ValueError("SearXNG response exceeded the size limit")
        payload = json.loads(body or b"{}")
        hits: list[SearchHit] = []
        for result in payload.get("results") or []:
            url = str(result.get("url") or "")
            if urlsplit(url).scheme not in {"http", "https"}:
                continue
            hits.append(
                SearchHit(
                    url=url,
                    title=str(result.get("title") or "")[:300],
                    snippet=str(result.get("content") or "")[:500],
                    provider=self.name,
                    rank=len(hits) + 1,
                    extra={
                        "engine": result.get("engine"),
                        "published": result.get("publishedDate"),
                    },
                )
            )
            if len(hits) >= limit:
                break
        return hits


class InternalKnowledgeProvider:
    """Nghiên cứu đã duyệt trong kho: nguồn tin cậy nội bộ, trích dẫn tới `/research/{id}`."""

    name = "internal_kb"

    def __init__(self, db: Session):
        self.db = db

    def search(self, query: str, *, limit: int) -> list[SearchHit]:
        terms = [term for term in _WORD.findall(query.casefold()) if len(term) > 3][:6]
        if not terms:
            return []
        items = list(
            self.db.scalars(
                select(ResearchItem)
                .where(
                    ResearchItem.status == "approved",
                    # Báo cáo do chính pipeline viết không được trích dẫn lại như nguồn gốc.
                    ResearchItem.type != "deep-research-report",
                )
                .order_by(ResearchItem.updated_at.desc())
                .limit(500)
            )
        )
        scored = []
        for item in items:
            haystack = f"{item.title} {item.summary or ''} {item.content[:20_000]}".casefold()
            score = sum(haystack.count(term) for term in terms)
            if score:
                scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            SearchHit(
                url=f"/research/{item.id}",
                title=item.title,
                snippet=(item.summary or "")[:500],
                provider=self.name,
                rank=rank,
                research_item_id=item.id,
                content=item.content,
            )
            for rank, (_, item) in enumerate(scored[:limit], start=1)
        ]


def providers_from_settings(db: Session) -> list[SearchProvider]:
    providers: list[SearchProvider] = []
    for name in (part.strip() for part in settings.research_search_providers.split(",")):
        if name == "searxng":
            providers.append(SearxngSearchProvider())
        elif name == "internal_kb":
            providers.append(InternalKnowledgeProvider(db))
    return providers


# --- Độ liên quan -----------------------------------------------------------------------------

_TERM = re.compile(r"[^\W_]{2,}", re.UNICODE)
STOPWORDS = frozenset(
    """the and for with from that this what how are was were has have into over your their about
    can will not but its our who why when which than then also more most such use using used via
    các của cho với trong những một như này được là và có không khi thì để theo về đến từ tại
    gì sao nào bao nhiêu thế ra đang đã sẽ""".split()
)


def content_terms(text: str) -> set[str]:
    return {term for term in (t.casefold() for t in _TERM.findall(text)) if term not in STOPWORDS}


def hit_relevance(query: str, hit: SearchHit) -> float:
    """Tỉ lệ từ khóa của truy vấn có trong tiêu đề/đoạn trích/URL của kết quả.

    Máy tìm kiếm miễn phí đôi khi trả kết quả chỉ khớp một từ (ví dụ "enterprise" → thuê xe);
    kết quả kiểu đó bị loại trước khi tốn công tải trang và gọi AI."""
    wanted = content_terms(query)
    if not wanted:
        return 1.0
    found = content_terms(f"{hit.title} {hit.snippet} {urlsplit(hit.url).path.replace('-', ' ')}")
    return len(wanted & found) / len(wanted)


def text_relevance(query_terms: set[str], text: str) -> int:
    """Số từ khóa khác nhau của truy vấn xuất hiện trong nội dung đã tải."""
    return len(query_terms & content_terms(text[:20_000]))


# --- Bộ nhớ đệm -------------------------------------------------------------------------------


def cache_key(kind: str, *parts: str) -> str:
    return hashlib.sha256("|".join((kind, *parts)).encode()).hexdigest()


def normalized_query(query: str) -> str:
    return " ".join(query.casefold().split())


def cache_get(db: Session, key: str) -> dict[str, Any] | None:
    row = db.scalar(select(ResearchWebCache).where(ResearchWebCache.cache_key == key))
    if row is None:
        return None
    expires_at = (
        row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=utcnow().tzinfo)
    )
    if expires_at <= utcnow():
        return None
    row.hit_count += 1
    return row.payload_json


def cache_put(db: Session, key: str, kind: str, payload: dict[str, Any], hours: float) -> None:
    if hours <= 0:
        return
    row = db.scalar(select(ResearchWebCache).where(ResearchWebCache.cache_key == key))
    expires_at = utcnow() + timedelta(hours=hours)
    if row is None:
        db.add(
            ResearchWebCache(kind=kind, cache_key=key, payload_json=payload, expires_at=expires_at)
        )
    else:
        row.payload_json = payload
        row.expires_at = expires_at


def purge_expired_cache(db: Session) -> int:
    result = db.execute(delete(ResearchWebCache).where(ResearchWebCache.expires_at <= utcnow()))
    return result.rowcount or 0


# --- Khử trùng --------------------------------------------------------------------------------


def registrable_domain(url: str) -> str:
    host = (urlsplit(url).hostname or "").casefold().removeprefix("www.")
    labels = host.split(".")
    if len(labels) >= 3 and labels[-2] in {"co", "com", "org", "net", "gov", "edu", "ac"}:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def canonical_url(url: str) -> str:
    if url.startswith("/research/"):
        return url
    try:
        return normalize_url(url)
    except Exception:  # noqa: BLE001 - URL lạ từ máy tìm kiếm không được làm hỏng cả lượt chạy
        return url


def content_fingerprint(text: str) -> str:
    return hashlib.sha256(" ".join(text.casefold().split()).encode()).hexdigest()


def simhash(text: str) -> str:
    """Simhash 64-bit trên shingle 4 từ để phát hiện bản sao gần giống (bài đăng lại)."""
    words = _WORD.findall(text.casefold())
    weights = [0] * 64
    for index in range(max(1, len(words) - 3)):
        shingle = " ".join(words[index : index + 4])
        value = int.from_bytes(hashlib.blake2b(shingle.encode(), digest_size=8).digest(), "big")
        for bit in range(64):
            weights[bit] += 1 if value >> bit & 1 else -1
    fingerprint = sum(1 << bit for bit, weight in enumerate(weights) if weight > 0)
    return f"{fingerprint:016x}"


def near_duplicate(left: str, right: str, *, max_distance: int = 3) -> bool:
    return bin(int(left, 16) ^ int(right, 16)).count("1") <= max_distance


def run_parallel(
    jobs: list[Callable[[], Any]], *, workers: int
) -> list[tuple[Any, BaseException | None]]:
    """Chạy các hàm chỉ làm I/O (không chạm phiên DB) song song, giữ nguyên thứ tự kết quả."""
    from concurrent.futures import ThreadPoolExecutor

    if workers <= 1 or len(jobs) <= 1:
        results: list[tuple[Any, BaseException | None]] = []
        for job in jobs:
            try:
                results.append((job(), None))
            except Exception as exc:  # noqa: BLE001
                results.append((None, exc))
        return results
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(job) for job in jobs]
        collected = []
        for future in futures:
            try:
                collected.append((future.result(), None))
            except Exception as exc:  # noqa: BLE001
                collected.append((None, exc))
        return collected
