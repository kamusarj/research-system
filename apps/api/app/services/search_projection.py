from __future__ import annotations

import hashlib
import math
import time
import uuid
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, TypeVar

import httpx
from pydantic import ValidationError
from sqlalchemy import Float, delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.observability import provider_observation
from app.models import DocumentGraphWorkspace, ResearchItem, SearchVectorProjection
from app.schemas.research import ResearchRead
from app.schemas.search import SearchDocument
from app.services.research import serialize_research


class SearchProjectionError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


ValueT = TypeVar("ValueT")


def _batches(values: list[ValueT], size: int) -> Iterator[list[ValueT]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _secret(value: Any) -> str:
    if value is None:
        return ""
    return value.get_secret_value().strip()


def _json_filter(field: str, value: str) -> str:
    # Meilisearch accepts JSON-compatible double-quoted string literals.
    import json

    return f"{field} = {json.dumps(value, ensure_ascii=False)}"


def build_search_documents(db: Session) -> list[SearchDocument]:
    items = list(
        db.scalars(
            select(ResearchItem)
            .options(selectinload(ResearchItem.tags))
            .where(ResearchItem.status == "approved")
            .order_by(ResearchItem.id)
        ).unique()
    )
    documents: list[SearchDocument] = []
    try:
        for item in items:
            if item.approved_at is None:
                raise ValueError("approved research is missing approved_at")
            documents.append(
                SearchDocument(
                    id=item.id,
                    display_id=item.display_id or item.id,
                    title=item.title,
                    summary=item.summary or "",
                    content=item.content[: settings.search_document_max_chars],
                    type=item.type,
                    collection_method=item.collection_method,
                    authors=item.authors or [],
                    tags=[tag.display_name for tag in item.tags],
                    tag_keys=[tag.name for tag in item.tags],
                    source_url=item.source_url,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    approved_at=item.approved_at,
                )
            )
    except (TypeError, ValueError, ValidationError) as exc:
        raise SearchProjectionError(
            "SEARCH_PROJECTION_INVALID",
            "The PostgreSQL search projection failed validation.",
        ) from exc
    return documents


def hydrate_ranked_research(db: Session, ids: list[str]) -> list[ResearchRead]:
    if not ids:
        return []
    items = list(
        db.scalars(
            select(ResearchItem)
            .options(selectinload(ResearchItem.tags))
            .where(ResearchItem.id.in_(ids), ResearchItem.status == "approved")
        ).unique()
    )
    by_id = {item.id: item for item in items}
    if len(by_id) != len(set(ids)):
        raise SearchProjectionError(
            "SEARCH_PROJECTION_MISMATCH",
            "The search projection references unavailable canonical research.",
        )
    return [serialize_research(by_id[item_id]) for item_id in ids]


class MeilisearchProjectionClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        index: str,
        batch_size: int,
        request_timeout: float,
        task_timeout: float,
        client_factory: Callable[..., httpx.Client] = httpx.Client,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.index = index
        self.batch_size = max(1, min(batch_size, 5_000))
        self.request_timeout = max(0.1, min(request_timeout, 60))
        self.task_timeout = max(1, min(task_timeout, 600))
        self.client_factory = client_factory
        self.sleep = sleep

    @classmethod
    def from_settings(cls) -> MeilisearchProjectionClient:
        base_url = (settings.meilisearch_url or "").strip()
        api_key = _secret(settings.meilisearch_api_key)
        index = settings.meilisearch_index.strip()
        if not base_url or not api_key or not index:
            raise SearchProjectionError(
                "MEILISEARCH_NOT_CONFIGURED",
                "The Meilisearch projection is not configured.",
            )
        return cls(
            base_url=base_url,
            api_key=api_key,
            index=index,
            batch_size=settings.meilisearch_batch_size,
            request_timeout=settings.meilisearch_request_timeout_seconds,
            task_timeout=settings.meilisearch_task_timeout_seconds,
        )

    def _client(self) -> httpx.Client:
        return self.client_factory(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.request_timeout,
        )

    @staticmethod
    def _payload(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise SearchProjectionError(
                "MEILISEARCH_RESPONSE_INVALID",
                "Meilisearch returned an invalid response.",
            ) from exc
        if not isinstance(payload, dict):
            raise SearchProjectionError(
                "MEILISEARCH_RESPONSE_INVALID",
                "Meilisearch returned an invalid response.",
            )
        return payload

    def _request(
        self,
        client: httpx.Client,
        method: str,
        path: str,
        *,
        allow_not_found: bool = False,
        **kwargs: Any,
    ) -> httpx.Response | None:
        try:
            response = client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise SearchProjectionError(
                "MEILISEARCH_UNAVAILABLE", "The Meilisearch projection is unavailable."
            ) from exc
        if allow_not_found and response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise SearchProjectionError(
                "MEILISEARCH_UNAVAILABLE", "The Meilisearch projection is unavailable."
            )
        return response

    def _wait_task(self, client: httpx.Client, response: httpx.Response) -> dict[str, Any]:
        payload = self._payload(response)
        task_uid = payload.get("taskUid")
        if not isinstance(task_uid, int):
            raise SearchProjectionError(
                "MEILISEARCH_RESPONSE_INVALID",
                "Meilisearch did not return a valid task identifier.",
            )
        deadline = time.monotonic() + self.task_timeout
        while time.monotonic() < deadline:
            task_response = self._request(client, "GET", f"/tasks/{task_uid}")
            assert task_response is not None
            task = self._payload(task_response)
            status = task.get("status")
            if status == "succeeded":
                return task
            if status in {"failed", "canceled"}:
                raise SearchProjectionError(
                    "MEILISEARCH_TASK_FAILED",
                    "A Meilisearch projection task failed.",
                )
            if status not in {"enqueued", "processing"}:
                raise SearchProjectionError(
                    "MEILISEARCH_RESPONSE_INVALID",
                    "Meilisearch returned an invalid task state.",
                )
            self.sleep(0.05)
        raise SearchProjectionError(
            "MEILISEARCH_TASK_TIMEOUT", "A Meilisearch projection task timed out."
        )

    def _delete_index(self, client: httpx.Client, index: str) -> None:
        existing = self._request(client, "GET", f"/indexes/{index}", allow_not_found=True)
        if existing is None:
            return
        response = self._request(client, "DELETE", f"/indexes/{index}", allow_not_found=True)
        if response is not None:
            self._wait_task(client, response)

    def _ensure_live_index(self, client: httpx.Client) -> None:
        existing = self._request(client, "GET", f"/indexes/{self.index}", allow_not_found=True)
        if existing is not None:
            return
        response = self._request(
            client,
            "POST",
            "/indexes",
            json={"uid": self.index, "primaryKey": "id"},
        )
        assert response is not None
        self._wait_task(client, response)

    def _count(self, client: httpx.Client, index: str) -> int:
        response = self._request(client, "GET", f"/indexes/{index}/stats")
        assert response is not None
        value = self._payload(response).get("numberOfDocuments")
        if not isinstance(value, int) or value < 0:
            raise SearchProjectionError(
                "MEILISEARCH_RESPONSE_INVALID",
                "Meilisearch returned an invalid document count.",
            )
        return value

    def rebuild(self, documents: list[SearchDocument]) -> dict[str, Any]:
        staging = f"{self.index}__staging"
        payloads = [document.model_dump(mode="json") for document in documents]
        with self._client() as client:
            self._delete_index(client, staging)
            create = self._request(
                client,
                "POST",
                "/indexes",
                json={"uid": staging, "primaryKey": "id"},
            )
            assert create is not None
            self._wait_task(client, create)
            settings_response = self._request(
                client,
                "PATCH",
                f"/indexes/{staging}/settings",
                json={
                    "searchableAttributes": [
                        "title",
                        "summary",
                        "content",
                        "authors",
                        "tags",
                    ],
                    "filterableAttributes": ["type", "collection_method", "tag_keys"],
                    "sortableAttributes": ["updated_at", "approved_at"],
                    "displayedAttributes": ["id", "title", "tags"],
                    "pagination": {"maxTotalHits": settings.search_max_results},
                },
            )
            assert settings_response is not None
            self._wait_task(client, settings_response)
            for batch in _batches(payloads, self.batch_size):
                addition = self._request(
                    client,
                    "POST",
                    f"/indexes/{staging}/documents",
                    params={"primaryKey": "id"},
                    json=batch,
                )
                assert addition is not None
                self._wait_task(client, addition)
            if self._count(client, staging) != len(payloads):
                raise SearchProjectionError(
                    "MEILISEARCH_PROJECTION_MISMATCH",
                    "The Meilisearch projection count check failed.",
                )
            self._ensure_live_index(client)
            swap = self._request(
                client,
                "POST",
                "/swap-indexes",
                json=[{"indexes": [self.index, staging]}],
            )
            assert swap is not None
            self._wait_task(client, swap)
            self._delete_index(client, staging)
            actual = self._count(client, self.index)
        if actual != len(payloads):
            raise SearchProjectionError(
                "MEILISEARCH_PROJECTION_MISMATCH",
                "The Meilisearch projection count check failed.",
            )
        return {"source": len(documents), "projected": actual, "provider": "meilisearch"}

    def search(
        self,
        *,
        query: str,
        page: int,
        page_size: int,
        type_filter: str | None,
        collection_method: str | None,
        tag: str | None,
    ) -> tuple[list[str], int]:
        filters: list[str] = []
        if type_filter:
            filters.append(_json_filter("type", type_filter))
        if collection_method:
            filters.append(_json_filter("collection_method", collection_method))
        if tag:
            filters.append(_json_filter("tag_keys", tag.lower()))
        search_payload: dict[str, Any] = {
            "q": query,
            "page": page,
            "hitsPerPage": page_size,
            "attributesToRetrieve": ["id"],
        }
        if filters:
            search_payload["filter"] = filters
        with self._client() as client:
            response = self._request(
                client,
                "POST",
                f"/indexes/{self.index}/search",
                json=search_payload,
            )
        assert response is not None
        payload = self._payload(response)
        hits = payload.get("hits")
        total = payload.get("totalHits")
        if not isinstance(hits, list) or not isinstance(total, int) or total < 0:
            raise SearchProjectionError(
                "MEILISEARCH_RESPONSE_INVALID", "Meilisearch returned an invalid search response."
            )
        ids = [hit.get("id") for hit in hits if isinstance(hit, dict)]
        if len(ids) != len(hits) or any(not isinstance(item_id, str) for item_id in ids):
            raise SearchProjectionError(
                "MEILISEARCH_RESPONSE_INVALID", "Meilisearch returned an invalid search response."
            )
        return ids, total

    def suggest(self, query: str) -> list[str]:
        with self._client() as client:
            response = self._request(
                client,
                "POST",
                f"/indexes/{self.index}/search",
                json={
                    "q": query,
                    "limit": 5,
                    "attributesToRetrieve": ["title", "tags"],
                },
            )
        assert response is not None
        hits = self._payload(response).get("hits")
        if not isinstance(hits, list):
            raise SearchProjectionError(
                "MEILISEARCH_RESPONSE_INVALID", "Meilisearch returned an invalid search response."
            )
        suggestions: list[str] = []
        for hit in hits:
            if not isinstance(hit, dict) or not isinstance(hit.get("title"), str):
                raise SearchProjectionError(
                    "MEILISEARCH_RESPONSE_INVALID",
                    "Meilisearch returned an invalid search response.",
                )
            suggestions.append(hit["title"])
            tags = hit.get("tags", [])
            if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
                raise SearchProjectionError(
                    "MEILISEARCH_RESPONSE_INVALID",
                    "Meilisearch returned an invalid search response.",
                )
            suggestions.extend(tags)
        return list(dict.fromkeys(suggestions))[:8]


class EmbeddingClient(Protocol):
    provider: str
    model: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def _embedding_options(api_key: str, *, gemini_model: bool) -> dict[str, Any]:
    if not api_key:
        raise SearchProjectionError(
            "EMBEDDING_NOT_CONFIGURED", "The search embedding provider is not configured."
        )
    if settings.search_embedding_dimensions != 1024:
        raise SearchProjectionError(
            "EMBEDDING_CONFIGURATION_INVALID",
            "The configured search embedding dimension is unsupported.",
        )
    # A provider switch that keeps the other provider's model name would only fail
    # later as an opaque upstream 4xx; reject the mismatch while loading settings.
    if settings.search_embedding_model.startswith("gemini-") != gemini_model:
        raise SearchProjectionError(
            "EMBEDDING_CONFIGURATION_INVALID",
            "The configured search embedding model does not match its provider.",
        )
    return {
        "api_key": api_key,
        "model": settings.search_embedding_model,
        "dimensions": settings.search_embedding_dimensions,
        "request_timeout": settings.ai_request_timeout,
        "batch_size": settings.search_embedding_batch_size,
        "request_retries": settings.search_embedding_request_retries,
        "retry_backoff_seconds": settings.search_embedding_retry_backoff_seconds,
    }


class _HttpEmbeddingClient:
    """Shared retry loop and vector validation for HTTP embedding providers."""

    provider = ""
    max_batch_size = 128

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        dimensions: int,
        request_timeout: float,
        batch_size: int,
        post: Callable[..., httpx.Response] = httpx.post,
        request_retries: int = 2,
        retry_backoff_seconds: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.request_timeout = request_timeout
        self.batch_size = max(1, min(batch_size, self.max_batch_size))
        self.post = post
        self.request_retries = max(0, min(request_retries, 5))
        self.retry_backoff_seconds = max(0, min(retry_backoff_seconds, 10))
        self.sleep = sleep

    def _request(self, texts: list[str]) -> tuple[str, dict[str, str], dict[str, Any]]:
        raise NotImplementedError

    def _vectors(self, payload: Any) -> list[Any]:
        raise NotImplementedError

    def _retry_delay(self, exc: Exception, attempt: int) -> float:
        return self.retry_backoff_seconds * (2**attempt)

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        url, headers, body = self._request(texts)
        response: httpx.Response | None = None
        for attempt in range(self.request_retries + 1):
            try:
                with provider_observation(
                    provider=self.provider, model=self.model, operation="embedding"
                ):
                    response = self.post(
                        url, headers=headers, json=body, timeout=self.request_timeout
                    )
                    response.raise_for_status()
                break
            except (httpx.HTTPError, OSError) as exc:
                retryable = not isinstance(exc, httpx.HTTPStatusError) or (
                    exc.response.status_code == 429 or exc.response.status_code >= 500
                )
                if not retryable or attempt >= self.request_retries:
                    raise SearchProjectionError(
                        "EMBEDDING_PROVIDER_UNAVAILABLE",
                        "The search embedding provider is unavailable.",
                    ) from exc
                self.sleep(self._retry_delay(exc, attempt))
        assert response is not None
        try:
            vectors = self._vectors(response.json())
        except (KeyError, TypeError, ValueError) as exc:
            raise SearchProjectionError(
                "EMBEDDING_RESPONSE_INVALID",
                "The search embedding provider returned an invalid response.",
            ) from exc
        if len(vectors) != len(texts):
            raise SearchProjectionError(
                "EMBEDDING_RESPONSE_INVALID",
                "The search embedding provider returned an invalid response.",
            )
        validated: list[list[float]] = []
        for vector in vectors:
            if (
                not isinstance(vector, list)
                or len(vector) != self.dimensions
                or any(
                    not isinstance(value, (int, float)) or not math.isfinite(value)
                    for value in vector
                )
            ):
                raise SearchProjectionError(
                    "EMBEDDING_RESPONSE_INVALID",
                    "The search embedding provider returned an invalid response.",
                )
            validated.append([float(value) for value in vector])
        return validated

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results: list[list[float]] = []
        for batch in _batches(texts, self.batch_size):
            results.extend(self._embed_batch(batch))
        return results

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


class MistralEmbeddingClient(_HttpEmbeddingClient):
    provider = "mistral"

    @classmethod
    def from_settings(cls) -> MistralEmbeddingClient:
        return cls(**_embedding_options(_secret(settings.mistral_api_key), gemini_model=False))

    def _request(self, texts: list[str]) -> tuple[str, dict[str, str], dict[str, Any]]:
        return (
            "https://api.mistral.ai/v1/embeddings",
            {"Authorization": f"Bearer {self.api_key}"},
            {"model": self.model, "input": texts},
        )

    def _vectors(self, payload: Any) -> list[Any]:
        data = sorted(payload["data"], key=lambda item: item["index"])
        return [item["embedding"] for item in data]


def _google_retry_delay(response: httpx.Response) -> float:
    """Seconds from a Google ``RetryInfo`` detail (``"37s"``) or ``Retry-After``; 0 if absent."""
    try:
        for detail in response.json()["error"]["details"]:
            if str(detail.get("@type", "")).endswith("google.rpc.RetryInfo"):
                delay = float(str(detail["retryDelay"]).removesuffix("s"))
                return delay if math.isfinite(delay) and delay > 0 else 0.0
    except (AttributeError, KeyError, TypeError, ValueError):
        pass
    try:
        delay = float(response.headers.get("retry-after", "0"))
    except ValueError:
        return 0.0
    return delay if math.isfinite(delay) and delay > 0 else 0.0


class GeminiEmbeddingClient(_HttpEmbeddingClient):
    """Gemini API embeddings (``gemini-embedding-2`` has a free tier).

    ``gemini-embedding-2`` takes no ``task_type``; asymmetric retrieval uses the
    documented text prefixes instead, so documents and queries must be embedded
    through ``embed`` and ``embed_query`` respectively. The API truncates the
    Matryoshka vector to ``outputDimensionality`` and normalizes it.
    """

    provider = "gemini"
    max_batch_size = 100
    # Free-tier 429s carry a RetryInfo delay; honour it, but never stall a chat or
    # search request for longer than this.
    max_retry_delay_seconds = 20.0

    @classmethod
    def from_settings(cls) -> GeminiEmbeddingClient:
        return cls(**_embedding_options(_secret(settings.gemini_api_key), gemini_model=True))

    def _request(self, texts: list[str]) -> tuple[str, dict[str, str], dict[str, Any]]:
        model = f"models/{self.model}"
        return (
            f"https://generativelanguage.googleapis.com/v1beta/{model}:batchEmbedContents",
            {"x-goog-api-key": self.api_key},
            {
                "requests": [
                    {
                        "model": model,
                        "content": {"parts": [{"text": text}]},
                        "outputDimensionality": self.dimensions,
                    }
                    for text in texts
                ]
            },
        )

    def _vectors(self, payload: Any) -> list[Any]:
        return [item["values"] for item in payload["embeddings"]]

    def _retry_delay(self, exc: Exception, attempt: int) -> float:
        delay = super()._retry_delay(exc, attempt)
        if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
            delay = max(delay, _google_retry_delay(exc.response))
        return min(delay, self.max_retry_delay_seconds)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return super().embed([f"title: none | text: {text}" for text in texts])

    def embed_query(self, text: str) -> list[float]:
        return super().embed([f"task: search result | query: {text}"])[0]


def embedding_client_from_settings() -> EmbeddingClient:
    if settings.search_embedding_provider == "gemini":
        return GeminiEmbeddingClient.from_settings()
    return MistralEmbeddingClient.from_settings()


def _split_on_word_boundaries(text: str, *, size: int, overlap: int, min_chars: int) -> list[str]:
    """Split text into bounded chunks that end and start on a whitespace boundary.

    The previous implementation used ``text[start:start+size]`` and cut mid-token.
    Word-boundary splits keep each chunk's start/end legible and reduce embedding
    noise. ``overlap`` carries the last ``overlap`` characters of one chunk into
    the next so a concept split across a boundary still appears in at least one
    chunk with full context. ``min_chars`` guards against shrinking a chunk below
    a useful size when the next whitespace is just past ``start``.
    """
    if not text or not text.strip():
        return []
    if len(text) <= size:
        return [text.strip()]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start + min_chars:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        step = end - start
        start = max(end - overlap, start + 1) if overlap else end
        if start <= end - step:
            start = end
    return chunks


def _document_chunks(document: SearchDocument) -> list[str]:
    head = "\n\n".join(
        value.strip() for value in (document.title, document.summary) if value.strip()
    )
    body = (document.content or "").strip()
    size = max(256, min(settings.search_embedding_chunk_chars, 16_000))
    overlap = max(0, min(settings.search_embedding_chunk_overlap_chars, size // 2))
    min_chars = max(1, min(settings.search_embedding_chunk_min_chars, size))
    limit = max(1, min(settings.search_embedding_max_chunks_per_item, 128))
    body_chunks = _split_on_word_boundaries(body, size=size, overlap=overlap, min_chars=min_chars)
    chunks: list[str] = []
    if head:
        chunks.append(head)
    chunks.extend(body_chunks)
    if not chunks:
        return [document.title]
    return chunks[:limit]


@dataclass(slots=True)
class VectorProjectionRow:
    id: str
    research_id: str
    chunk_index: int
    content: str
    content_hash: str
    embedding: list[float]
    source_updated_at: datetime


class PgvectorProjection:
    def __init__(self, embedding_client: EmbeddingClient) -> None:
        self.embedding_client = embedding_client

    def _rows(self, documents: list[SearchDocument]) -> list[VectorProjectionRow]:
        sources: list[tuple[SearchDocument, int, str]] = []
        for document in documents:
            sources.extend(
                (document, chunk_index, chunk)
                for chunk_index, chunk in enumerate(_document_chunks(document))
            )
        vectors = self.embedding_client.embed([chunk for _, _, chunk in sources])
        if len(vectors) != len(sources):
            raise SearchProjectionError(
                "EMBEDDING_RESPONSE_INVALID",
                "The search embedding provider returned an invalid response.",
            )
        return [
            VectorProjectionRow(
                id=f"{document.id}:{chunk_index}",
                research_id=document.id,
                chunk_index=chunk_index,
                content=chunk,
                content_hash=hashlib.sha256(chunk.encode()).hexdigest(),
                embedding=vector,
                source_updated_at=document.updated_at,
            )
            for (document, chunk_index, chunk), vector in zip(sources, vectors, strict=True)
        ]

    def rebuild(self, db: Session, documents: list[SearchDocument]) -> dict[str, Any]:
        rows = self._rows(documents)
        sync_id = str(uuid.uuid4())
        try:
            # Approved search is a rebuildable projection, while draft document
            # chunks are a scoped RAG cache. Preserve only draft workspace rows;
            # an approved document is replaced by the normal approved rebuild.
            draft_document_ids = (
                select(DocumentGraphWorkspace.research_id)
                .join(ResearchItem, ResearchItem.id == DocumentGraphWorkspace.research_id)
                .where(ResearchItem.status != "approved")
            )
            db.execute(
                delete(SearchVectorProjection).where(
                    SearchVectorProjection.research_id.not_in(draft_document_ids)
                )
            )
            db.add_all(
                [
                    SearchVectorProjection(
                        id=row.id,
                        research_id=row.research_id,
                        chunk_index=row.chunk_index,
                        content=row.content,
                        content_hash=row.content_hash,
                        embedding=row.embedding,
                        provider=self.embedding_client.provider,
                        model=self.embedding_client.model,
                        source_updated_at=row.source_updated_at,
                        sync_id=sync_id,
                    )
                    for row in rows
                ]
            )
            db.flush()
            projected_ids = [document.id for document in documents]
            actual = (
                db.scalar(
                    select(func.count())
                    .select_from(SearchVectorProjection)
                    .where(SearchVectorProjection.research_id.in_(projected_ids))
                )
                if projected_ids
                else 0
            ) or 0
            if actual != len(rows):
                raise SearchProjectionError(
                    "PGVECTOR_PROJECTION_MISMATCH",
                    "The pgvector projection count check failed.",
                )
            db.commit()
        except SearchProjectionError:
            db.rollback()
            raise
        except (SQLAlchemyError, ValueError) as exc:
            db.rollback()
            raise SearchProjectionError(
                "PGVECTOR_UNAVAILABLE", "The pgvector projection is unavailable."
            ) from exc
        return {
            "source": len(documents),
            "projected": len({row.research_id for row in rows}),
            "chunks": actual,
            "provider": "pgvector",
            "model": self.embedding_client.model,
        }

    def replace_document(self, db: Session, document: SearchDocument) -> int:
        """Atomically replace one document's scoped vector chunks."""
        rows = self._rows([document])
        sync_id = str(uuid.uuid4())
        try:
            db.execute(
                delete(SearchVectorProjection).where(
                    SearchVectorProjection.research_id == document.id
                )
            )
            db.add_all(
                [
                    SearchVectorProjection(
                        id=row.id,
                        research_id=row.research_id,
                        chunk_index=row.chunk_index,
                        content=row.content,
                        content_hash=row.content_hash,
                        embedding=row.embedding,
                        provider=self.embedding_client.provider,
                        model=self.embedding_client.model,
                        source_updated_at=row.source_updated_at,
                        sync_id=sync_id,
                    )
                    for row in rows
                ]
            )
            db.flush()
        except SearchProjectionError:
            raise
        except (SQLAlchemyError, ValueError) as exc:
            raise SearchProjectionError(
                "PGVECTOR_UNAVAILABLE", "The pgvector projection is unavailable."
            ) from exc
        return len(rows)

    def _search_chunks(
        self,
        db: Session,
        vector: list[float],
        *,
        limit: int,
        research_id: str | None = None,
        approved_only: bool = False,
    ) -> list[tuple[str, str, str, float]]:
        """Return ``(chunk_id, research_id, content, distance)`` by ascending distance.

        ``distance`` is pgvector cosine distance (``<=>``): smaller is better and
        ``similarity = 1 - distance``. When ``research_id`` is supplied the query
        is restricted to that document's chunks; chat-scope passage retrieval uses
        this so a document-scoped session never reads another document.
        """
        distance = SearchVectorProjection.embedding.op("<=>", return_type=Float())(vector)
        statement = select(
            SearchVectorProjection.id,
            SearchVectorProjection.research_id,
            SearchVectorProjection.content,
            distance.label("distance"),
        )
        # Vectors from another provider/model share the column but not the space;
        # until they are re-indexed they must not be ranked against this query.
        statement = statement.where(
            SearchVectorProjection.provider == self.embedding_client.provider,
            SearchVectorProjection.model == self.embedding_client.model,
        ).order_by("distance")
        if research_id is not None:
            statement = statement.where(SearchVectorProjection.research_id == research_id)
        if approved_only:
            statement = statement.join(
                ResearchItem, ResearchItem.id == SearchVectorProjection.research_id
            ).where(ResearchItem.status == "approved")
        fetch = min(max(limit * 3, 10), settings.search_max_results)
        statement = statement.limit(fetch)
        try:
            rows = list(db.execute(statement).all())
        except (SQLAlchemyError, ValueError) as exc:
            raise SearchProjectionError(
                "PGVECTOR_UNAVAILABLE", "The pgvector projection is unavailable."
            ) from exc
        return [
            (str(row.id), str(row.research_id), str(row.content), float(row.distance))
            for row in rows
        ]

    @staticmethod
    def _mmr_select(
        candidates: list[tuple[str, str, str, float]],
        *,
        lambda_mmr: float,
        limit: int,
    ) -> list[str]:
        """Maximal Marginal Relevance selection over chunk candidates.

        ``candidates`` are ``(chunk_id, research_id, content, distance)`` ordered
        by ascending distance to the query. With ``lambda_mmr >= 1.0`` or without
        a per-chunk embedding lookup we fall back to plain distance order, which
        still preserves the distance cutoff and never breaks the shape contract.
        The pairwise diversity term uses chunk content overlap as a cheap proxy
        when available, bounded so cost stays linear-ish in ``limit``.
        """
        if not candidates:
            return []
        lambda_mmr = max(0.0, min(lambda_mmr, 1.0))
        if lambda_mmr >= 1.0:
            seen: set[str] = set()
            ordered: list[str] = []
            for chunk_id, _, _, _ in candidates:
                if chunk_id in seen:
                    continue
                ordered.append(chunk_id)
                seen.add(chunk_id)
            return ordered[:limit]

        def _sim_to_query(distance: float) -> float:
            return max(0.0, 1.0 - distance)

        def _content_overlap(left: str, right: str) -> float:
            left_words = set(left.lower().split())
            right_words = set(right.lower().split())
            if not left_words or not right_words:
                return 0.0
            return len(left_words & right_words) / len(left_words | right_words)

        selected: list[str] = []
        remaining = list(candidates)
        while remaining and len(selected) < limit:
            best_index = 0
            best_score = -float("inf")
            for index, (_chunk_id, _research_id, content, distance) in enumerate(remaining):
                relevance = lambda_mmr * _sim_to_query(distance)
                redundancy = 0.0
                if selected:
                    selected_contents = [
                        next(
                            (s_content for s_id, _r, s_content, _d in candidates if s_id == sid),
                            "",
                        )
                        for sid in selected
                    ]
                    overlaps = [_content_overlap(content, sc) for sc in selected_contents]
                    redundancy = max(overlaps) if overlaps else 0.0
                score = relevance - (1.0 - lambda_mmr) * redundancy
                if score > best_score:
                    best_score = score
                    best_index = index
            chosen_id = remaining[best_index][0]
            selected.append(chosen_id)
            remaining.pop(best_index)
        return selected

    def search(self, db: Session, query: str, limit: int) -> list[str]:
        vector = self.embedding_client.embed_query(query)
        max_distance = max(0.0, min(settings.search_semantic_max_distance, 2.0))
        lambda_mmr = settings.search_mmr_lambda
        candidates = self._search_chunks(db, vector, limit=limit, approved_only=True)
        candidates = [c for c in candidates if c[3] <= max_distance]
        selected_chunk_ids = self._mmr_select(candidates, lambda_mmr=lambda_mmr, limit=limit)
        candidate_by_id = {chunk_id: research_id for chunk_id, research_id, _c, _d in candidates}
        research_order: list[str] = []
        seen_research: set[str] = set()
        for chunk_id in selected_chunk_ids:
            research_id = candidate_by_id.get(chunk_id)
            if research_id is None or research_id in seen_research:
                continue
            research_order.append(research_id)
            seen_research.add(research_id)
        return research_order[:limit]

    def search_chunks(
        self, db: Session, *, query: str, research_id: str, limit: int
    ) -> list[tuple[str, str, float]]:
        """Return ``(chunk_id, content, distance)`` for one document's chunks.

        Used by ``graph_chat.build_scope_context`` so a document-scoped chat
        retrieves only passages of the bound document. Distance cutoff and MMR
        are not applied here: chat-scope wants the top-k passages by relevance to
        the current user message, not a diversified cross-document set.
        """
        vector = self.embedding_client.embed_query(query)
        rows = self._search_chunks(db, vector, limit=limit, research_id=research_id)
        return [(chunk_id, content, distance) for chunk_id, _rid, content, distance in rows]


def rebuild_search_projections(
    db: Session,
    projections: Iterable[str],
    *,
    meilisearch_factory: Callable[[], MeilisearchProjectionClient] = (
        MeilisearchProjectionClient.from_settings
    ),
    embedding_factory: Callable[[], EmbeddingClient] = embedding_client_from_settings,
) -> dict[str, dict[str, Any]]:
    documents = build_search_documents(db)
    result: dict[str, dict[str, Any]] = {}
    selected = list(projections)
    if "meilisearch" in selected:
        result["meilisearch"] = meilisearch_factory().rebuild(documents)
    if "pgvector" in selected:
        result["pgvector"] = PgvectorProjection(embedding_factory()).rebuild(db, documents)
    return result
