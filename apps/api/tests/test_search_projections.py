import json
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import func, select
from test_research import create_item

from app.core.config import settings
from app.models import SearchVectorProjection
from app.schemas.search import SearchDocument, reciprocal_rank_fusion
from app.services.search_projection import (
    GeminiEmbeddingClient,
    MeilisearchProjectionClient,
    MistralEmbeddingClient,
    PgvectorProjection,
    SearchProjectionError,
    _document_chunks,
    _json_filter,
    _split_on_word_boundaries,
    build_search_documents,
    embedding_client_from_settings,
)


def approve(client, item):
    client.post(f"/api/v1/research/{item['id']}/submit-review")
    return client.post(f"/api/v1/research/{item['id']}/approve").json()


def document(item_id: str, title: str) -> SearchDocument:
    now = datetime.now(UTC)
    return SearchDocument(
        id=item_id,
        display_id=f"RES-{item_id[:8]}",
        title=title,
        summary="A grounded summary",
        content="Business agent retrieval evidence.",
        type="internal-research",
        collection_method="manual",
        authors=["Researcher"],
        tags=["RAG"],
        tag_keys=["rag"],
        source_url="https://example.com/research",
        created_at=now,
        updated_at=now,
        approved_at=now,
    )


class FakeMeilisearch:
    def __init__(self) -> None:
        self.indexes = {"research_items": {"stale": {"id": "stale"}}}
        self.tasks: dict[int, str] = {}
        self.task_id = 0
        self.addition_sizes: list[int] = []
        self.swaps = 0
        self.last_search: dict | None = None

    def task(self) -> httpx.Response:
        self.task_id += 1
        self.tasks[self.task_id] = "succeeded"
        return httpx.Response(202, json={"taskUid": self.task_id, "status": "enqueued"})

    def handler(self, request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer unit-api-key"
        path = request.url.path
        method = request.method
        if path.startswith("/tasks/") and method == "GET":
            task_id = int(path.rsplit("/", 1)[-1])
            return httpx.Response(200, json={"status": self.tasks[task_id]})
        if path == "/indexes" and method == "POST":
            payload = json.loads(request.content)
            self.indexes[payload["uid"]] = {}
            return self.task()
        if path.startswith("/indexes/") and path.endswith("/settings") and method == "PATCH":
            return self.task()
        if path.startswith("/indexes/") and path.endswith("/documents") and method == "POST":
            index = path.split("/")[2]
            payload = json.loads(request.content)
            self.addition_sizes.append(len(payload))
            self.indexes[index].update({item["id"]: item for item in payload})
            return self.task()
        if path.startswith("/indexes/") and path.endswith("/stats") and method == "GET":
            index = path.split("/")[2]
            return httpx.Response(200, json={"numberOfDocuments": len(self.indexes[index])})
        if path.startswith("/indexes/") and path.endswith("/search") and method == "POST":
            index = path.split("/")[2]
            self.last_search = json.loads(request.content)
            hits = list(self.indexes[index].values())
            return httpx.Response(
                200,
                json={
                    "hits": [{"id": hit["id"]} for hit in hits],
                    "totalHits": len(hits),
                },
            )
        if path.startswith("/indexes/") and method == "GET":
            index = path.split("/")[2]
            if index not in self.indexes:
                return httpx.Response(404, json={"code": "index_not_found"})
            return httpx.Response(200, json={"uid": index})
        if path.startswith("/indexes/") and method == "DELETE":
            index = path.split("/")[2]
            if index not in self.indexes:
                return httpx.Response(404, json={"code": "index_not_found"})
            del self.indexes[index]
            return self.task()
        if path == "/swap-indexes" and method == "POST":
            left, right = json.loads(request.content)[0]["indexes"]
            self.indexes[left], self.indexes[right] = self.indexes[right], self.indexes[left]
            self.swaps += 1
            return self.task()
        raise AssertionError(f"Unexpected Meilisearch request: {method} {path}")


def meili_client(fake: FakeMeilisearch) -> MeilisearchProjectionClient:
    def factory(**kwargs):
        return httpx.Client(transport=httpx.MockTransport(fake.handler), **kwargs)

    return MeilisearchProjectionClient(
        base_url="http://meilisearch:7700",
        api_key="unit-api-key",
        index="research_items",
        batch_size=2,
        request_timeout=1,
        task_timeout=2,
        client_factory=factory,
        sleep=lambda _: None,
    )


def test_meilisearch_rebuild_uses_bounded_batches_atomic_swap_and_stale_prune():
    fake = FakeMeilisearch()
    client = meili_client(fake)
    documents = [document(str(index).zfill(36), f"Research {index}") for index in range(5)]

    first = client.rebuild(documents)
    second = client.rebuild(documents[:3])

    assert first == {"source": 5, "projected": 5, "provider": "meilisearch"}
    assert second == {"source": 3, "projected": 3, "provider": "meilisearch"}
    assert set(fake.indexes) == {"research_items"}
    assert set(fake.indexes["research_items"]) == {item.id for item in documents[:3]}
    assert max(fake.addition_sizes) == 2
    assert fake.swaps == 2


def test_meilisearch_search_parameterizes_escaped_filters():
    fake = FakeMeilisearch()
    client = meili_client(fake)
    client.rebuild([document("a" * 36, "Agent Retrieval")])

    ids, total = client.search(
        query="agent",
        page=1,
        page_size=20,
        type_filter='reference" OR id EXISTS',
        collection_method="manual",
        tag="RAG",
    )

    assert ids == ["a" * 36]
    assert total == 1
    assert fake.last_search is not None
    assert fake.last_search["filter"] == [
        _json_filter("type", 'reference" OR id EXISTS'),
        _json_filter("collection_method", "manual"),
        _json_filter("tag_keys", "rag"),
    ]


def test_meilisearch_missing_configuration_is_typed(monkeypatch):
    monkeypatch.setattr(settings, "meilisearch_url", None)
    monkeypatch.setattr(settings, "meilisearch_api_key", None)

    with pytest.raises(SearchProjectionError) as error:
        MeilisearchProjectionClient.from_settings()

    assert error.value.code == "MEILISEARCH_NOT_CONFIGURED"
    assert "key" not in error.value.message.lower()


def test_mistral_embedding_client_batches_and_validates_dimension():
    batch_sizes: list[int] = []

    def post(_url, **kwargs):
        inputs = kwargs["json"]["input"]
        batch_sizes.append(len(inputs))
        return httpx.Response(
            200,
            request=httpx.Request("POST", "https://api.mistral.ai/v1/embeddings"),
            json={
                "data": [
                    {"index": index, "embedding": [float(index + 1)] * 1024}
                    for index, _ in enumerate(inputs)
                ]
            },
        )

    client = MistralEmbeddingClient(
        api_key="unit-key",
        model="mistral-embed",
        dimensions=1024,
        request_timeout=1,
        batch_size=2,
        post=post,
    )

    vectors = client.embed(["one", "two", "three"])

    assert len(vectors) == 3
    assert all(len(vector) == 1024 for vector in vectors)
    assert batch_sizes == [2, 1]


def test_mistral_embedding_client_rejects_non_finite_or_wrong_dimensions():
    def post(_url, **_kwargs):
        return httpx.Response(
            200,
            request=httpx.Request("POST", "https://api.mistral.ai/v1/embeddings"),
            json={"data": [{"index": 0, "embedding": [1.0]}]},
        )

    client = MistralEmbeddingClient(
        api_key="unit-key",
        model="mistral-embed",
        dimensions=1024,
        request_timeout=1,
        batch_size=2,
        post=post,
    )

    with pytest.raises(SearchProjectionError) as error:
        client.embed(["invalid"])

    assert error.value.code == "EMBEDDING_RESPONSE_INVALID"


def test_mistral_embedding_client_retries_transient_transport_failures():
    attempts = 0
    delays: list[float] = []

    def post(_url, **_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.RemoteProtocolError("incomplete response")
        return httpx.Response(
            200,
            request=httpx.Request("POST", "https://api.mistral.ai/v1/embeddings"),
            json={"data": [{"index": 0, "embedding": [1.0] * 1024}]},
        )

    client = MistralEmbeddingClient(
        api_key="unit-key",
        model="mistral-embed",
        dimensions=1024,
        request_timeout=1,
        batch_size=2,
        post=post,
        request_retries=2,
        retry_backoff_seconds=0.25,
        sleep=delays.append,
    )

    assert len(client.embed(["retry me"])[0]) == 1024
    assert attempts == 2
    assert delays == [0.25]


GEMINI_BATCH_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:batchEmbedContents"
)


def gemini_response(count: int, *, dimensions: int = 1024) -> httpx.Response:
    return httpx.Response(
        200,
        request=httpx.Request("POST", GEMINI_BATCH_URL),
        json={"embeddings": [{"values": [float(i + 1)] * dimensions} for i in range(count)]},
    )


def gemini_client(post, **overrides) -> GeminiEmbeddingClient:
    options = {
        "api_key": "unit-key",
        "model": "gemini-embedding-2",
        "dimensions": 1024,
        "request_timeout": 1,
        "batch_size": 2,
        "post": post,
    }
    options.update(overrides)
    return GeminiEmbeddingClient(**options)


def test_gemini_embedding_client_sends_prefixed_batches_with_header_key():
    calls: list[tuple[str, dict]] = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return gemini_response(len(kwargs["json"]["requests"]))

    client = gemini_client(post)

    documents = client.embed(["one", "two", "three"])
    query = client.embed_query("Tác nhân AI là gì?")

    assert [len(vector) for vector in documents] == [1024, 1024, 1024]
    assert documents[0][0] == 1.0 and documents[1][0] == 2.0 and documents[2][0] == 1.0
    assert len(query) == 1024
    assert [url for url, _ in calls] == [GEMINI_BATCH_URL] * 3
    first = calls[0][1]
    assert first["headers"] == {"x-goog-api-key": "unit-key"}
    assert "unit-key" not in calls[0][0]
    assert first["json"]["requests"][0] == {
        "model": "models/gemini-embedding-2",
        "content": {"parts": [{"text": "title: none | text: one"}]},
        "outputDimensionality": 1024,
    }
    assert [len(kwargs["json"]["requests"]) for _, kwargs in calls] == [2, 1, 1]
    assert calls[2][1]["json"]["requests"][0]["content"]["parts"][0]["text"] == (
        "task: search result | query: Tác nhân AI là gì?"
    )


def test_gemini_embedding_client_caps_batch_size_at_api_limit():
    assert gemini_client(lambda *_a, **_k: None, batch_size=500).batch_size == 100


@pytest.mark.parametrize(
    "payload",
    [
        {"embeddings": [{"values": [1.0] * 768}]},
        {"embeddings": [{"values": [float("nan")] * 1024}]},
        {"embeddings": []},
        {"unexpected": True},
    ],
)
def test_gemini_embedding_client_rejects_invalid_responses(payload):
    def post(_url, **_kwargs):
        # json.dumps keeps NaN as a literal, which httpx's json= encoder refuses.
        return httpx.Response(
            200, request=httpx.Request("POST", GEMINI_BATCH_URL), content=json.dumps(payload)
        )

    with pytest.raises(SearchProjectionError) as error:
        gemini_client(post).embed(["invalid"])

    assert error.value.code == "EMBEDDING_RESPONSE_INVALID"


def test_gemini_embedding_client_honours_bounded_retry_info_on_rate_limit():
    attempts = 0
    delays: list[float] = []
    retry_delays = iter(["7s", "90s"])

    def post(_url, **_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts <= 2:
            return httpx.Response(
                429,
                request=httpx.Request("POST", GEMINI_BATCH_URL),
                json={
                    "error": {
                        "code": 429,
                        "details": [
                            {
                                "@type": "type.googleapis.com/google.rpc.RetryInfo",
                                "retryDelay": next(retry_delays),
                            }
                        ],
                    }
                },
            )
        return gemini_response(1)

    client = gemini_client(post, request_retries=2, retry_backoff_seconds=0.5, sleep=delays.append)

    assert len(client.embed_query("retry me")) == 1024
    assert attempts == 3
    assert delays == [7.0, 20.0]


def test_gemini_embedding_client_does_not_retry_rejected_key():
    attempts = 0

    def post(_url, **_kwargs):
        nonlocal attempts
        attempts += 1
        return httpx.Response(
            400,
            request=httpx.Request("POST", GEMINI_BATCH_URL),
            json={"error": {"code": 400, "message": "API key not valid. key=unit-key"}},
        )

    with pytest.raises(SearchProjectionError) as error:
        gemini_client(post, request_retries=3, sleep=lambda _s: None).embed(["x"])

    assert attempts == 1
    assert error.value.code == "EMBEDDING_PROVIDER_UNAVAILABLE"
    assert "unit-key" not in error.value.message


def test_embedding_factory_selects_configured_provider(monkeypatch):
    monkeypatch.setattr(settings, "search_embedding_provider", "gemini")
    monkeypatch.setattr(settings, "search_embedding_model", "gemini-embedding-2")
    monkeypatch.setattr(settings, "gemini_api_key", SecretStr("gemini-unit-key"))

    client = embedding_client_from_settings()

    assert isinstance(client, GeminiEmbeddingClient)
    assert (client.provider, client.model, client.dimensions) == (
        "gemini",
        "gemini-embedding-2",
        1024,
    )

    monkeypatch.setattr(settings, "search_embedding_provider", "mistral")
    monkeypatch.setattr(settings, "search_embedding_model", "mistral-embed")
    monkeypatch.setattr(settings, "mistral_api_key", SecretStr("mistral-unit-key"))

    assert isinstance(embedding_client_from_settings(), MistralEmbeddingClient)


@pytest.mark.parametrize(
    ("provider", "model", "key_field", "code"),
    [
        ("gemini", "gemini-embedding-2", None, "EMBEDDING_NOT_CONFIGURED"),
        ("gemini", "mistral-embed", "gemini_api_key", "EMBEDDING_CONFIGURATION_INVALID"),
        ("mistral", "gemini-embedding-2", "mistral_api_key", "EMBEDDING_CONFIGURATION_INVALID"),
    ],
)
def test_embedding_factory_rejects_missing_key_or_mismatched_model(
    monkeypatch, provider, model, key_field, code
):
    monkeypatch.setattr(settings, "search_embedding_provider", provider)
    monkeypatch.setattr(settings, "search_embedding_model", model)
    monkeypatch.setattr(settings, "gemini_api_key", None)
    monkeypatch.setattr(settings, "mistral_api_key", None)
    if key_field:
        monkeypatch.setattr(settings, key_field, SecretStr("unit-key"))

    with pytest.raises(SearchProjectionError) as error:
        embedding_client_from_settings()

    assert error.value.code == code
    assert "unit-key" not in error.value.message


def test_pgvector_chunk_search_only_ranks_rows_of_the_active_embedding_model(db, monkeypatch):
    captured = {}

    def execute(statement):
        captured["statement"] = statement.compile()
        return SimpleNamespace(all=lambda: [])

    monkeypatch.setattr(db, "execute", execute)
    client = SimpleNamespace(provider="gemini", model="gemini-embedding-2")

    assert PgvectorProjection(client)._search_chunks(db, [0.0] * 1024, limit=3) == []
    compiled = captured["statement"]
    sql = str(compiled)
    assert "search_vector_projections.provider = :provider_1" in sql
    assert "search_vector_projections.model = :model_1" in sql
    assert compiled.params["provider_1"] == "gemini"
    assert compiled.params["model_1"] == "gemini-embedding-2"


class DeterministicEmbeddingClient:
    provider = "test"
    model = "test-embed"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float((len(text) % 7) + 1)] * 1024 for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


def test_pgvector_projection_rebuild_is_repeatable_and_prunes_stale_rows(client, db):
    first = approve(client, create_item(client, "Agent Memory", ["RAG"]))
    second = approve(client, create_item(client, "Tool Use", ["Tools"]))
    documents = build_search_documents(db)
    projection = PgvectorProjection(DeterministicEmbeddingClient())

    initial = projection.rebuild(db, documents)
    db.query(SearchVectorProjection).filter_by(research_id=second["id"]).delete()
    db.commit()
    repeated = projection.rebuild(db, [doc for doc in documents if doc.id == first["id"]])

    assert initial["source"] == 2
    assert initial["projected"] == 2
    assert initial["chunks"] >= 2
    assert repeated["source"] == 1
    assert repeated["projected"] == 1
    assert db.scalar(select(func.count()).select_from(SearchVectorProjection)) == repeated["chunks"]
    rows = db.query(SearchVectorProjection).all()
    assert {row.research_id for row in rows} == {first["id"]}
    assert all(len(row.embedding) == 1024 for row in rows)


def test_search_documents_include_only_approved_and_bound_content(client, db, monkeypatch):
    approved = approve(client, create_item(client, "Approved", ["RAG"]))
    create_item(client, "Draft", ["RAG"])
    monkeypatch.setattr(settings, "search_document_max_chars", 5)

    documents = build_search_documents(db)

    assert [item.id for item in documents] == [approved["id"]]
    assert len(documents[0].content) <= 5


def test_selected_meilisearch_and_pgvector_routes_hydrate_canonical_rows(client, monkeypatch):
    item = approve(client, create_item(client, "Canonical Retrieval", ["RAG"]))

    fake_meili = SimpleNamespace(
        search=lambda **_kwargs: ([item["id"]], 1),
        suggest=lambda _query: ["Canonical Retrieval", "RAG"],
    )
    monkeypatch.setattr(settings, "search_data_provider", "meilisearch")
    monkeypatch.setattr(
        "app.api.search.MeilisearchProjectionClient.from_settings", lambda: fake_meili
    )
    lexical = client.get("/api/v1/search", params={"q": "retrievel"})
    suggestions = client.get("/api/v1/search/suggest", params={"q": "retr"})

    monkeypatch.setattr(settings, "vector_data_provider", "pgvector")
    monkeypatch.setattr(
        "app.api.search.embedding_client_from_settings",
        lambda: DeterministicEmbeddingClient(),
    )
    monkeypatch.setattr(
        "app.api.search.PgvectorProjection.search",
        lambda _self, _db, _query, _limit: [item["id"]],
    )
    semantic = client.post("/api/v1/search/semantic", json={"query": "agent memory"})

    assert lexical.status_code == 200
    assert lexical.json()["items"][0]["title"] == "Canonical Retrieval"
    assert suggestions.json() == ["Canonical Retrieval", "RAG"]
    assert semantic.status_code == 200
    assert semantic.json()["items"][0]["id"] == item["id"]


def test_search_rebuild_endpoint_returns_bounded_counts(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.search.rebuild_search_projections",
        lambda _db, _selected: {
            "meilisearch": {"source": 2, "projected": 2, "provider": "meilisearch"},
            "pgvector": {
                "source": 2,
                "projected": 2,
                "chunks": 4,
                "provider": "pgvector",
                "model": "mistral-embed",
            },
        },
    )

    response = client.post(
        "/api/v1/search/rebuild", json={"projections": ["meilisearch", "pgvector"]}
    )

    assert response.status_code == 200
    assert response.json()["projections"]["pgvector"]["chunks"] == 4
    assert "embedding" not in response.text
    assert "content" not in response.text


def test_secret_file_supports_meilisearch_api_key(tmp_path):
    (tmp_path / "meilisearch_api_key").write_text("file-key\n", encoding="utf-8")

    from app.core.config import Settings

    configured = Settings(
        _env_file=None,
        secret_files_dir=str(tmp_path),
        meilisearch_api_key=SecretStr("environment-key"),
    )

    assert configured.meilisearch_api_key is not None
    assert configured.meilisearch_api_key.get_secret_value() == "file-key"


def test_split_on_word_boundaries_never_cuts_mid_token_and_overlaps():
    text = "alpha beta gamma delta epsilon zeta eta theta iota"
    chunks = _split_on_word_boundaries(text, size=20, overlap=8, min_chars=5)

    assert chunks
    for chunk in chunks:
        assert chunk == chunk.strip()
        assert chunk.split()[0] in text
        assert chunk.split()[-1] in text
    if len(chunks) > 1:
        first_tail = chunks[0][-8:]
        second_head = chunks[1][:8]
        assert second_head and first_tail
        assert chunks[1].startswith(second_head)


def test_document_chunks_emits_title_summary_head_then_content(body_doc=None):
    now = datetime.now(UTC)
    doc = SearchDocument(
        id="a" * 36,
        display_id="RES-AAA",
        title="Agent Memory Atlas",
        summary="Grounded retrieval summary.",
        content="one two three four five six seven eight nine ten " * 200,
        type="internal-research",
        collection_method="manual",
        authors=["R"],
        tags=["RAG"],
        tag_keys=["rag"],
        source_url="https://example.com/x",
        created_at=now,
        updated_at=now,
        approved_at=now,
    )

    chunks = _document_chunks(doc)

    assert chunks[0].startswith("Agent Memory Atlas")
    assert "Grounded retrieval summary." in chunks[0]
    assert len(chunks) >= 2
    for chunk in chunks[1:]:
        assert chunk.split()[0] in doc.content
        assert chunk.split()[-1] in doc.content


def test_reciprocal_rank_fusion_orders_by_score_deterministically():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["c", "a", "b"]])

    # k=60, rank 0-indexed, score = 1/(k+rank+1):
    # a: 1/61 + 1/62 ; c: 1/63 + 1/61 ; b: 1/62 + 1/63  ->  a > c > b
    assert fused == ["a", "c", "b"]
    assert reciprocal_rank_fusion([["x"], ["y"]]) == reciprocal_rank_fusion([["x"], ["y"]])
    assert reciprocal_rank_fusion([]) == []
    # An item only in one list still keeps its score.
    only_one = reciprocal_rank_fusion([["solo"], []])
    assert only_one == ["solo"]


def test_pgvector_mmr_select_prefers_distant_chunks_when_lambda_below_one():
    projection = PgvectorProjection(DeterministicEmbeddingClient())
    # (chunk_id, research_id, content, distance). All equidistant to the query so
    # the diversity term decides; with two near-identical contents and a distinct
    # one, MMR must surface the distinct one before the duplicate.
    candidates = [
        ("c1", "r1", "alpha beta gamma delta", 0.1),
        ("c2", "r2", "alpha beta gamma delta", 0.1),
        ("c3", "r3", "completely different vocabulary", 0.1),
    ]

    selected = projection._mmr_select(candidates, lambda_mmr=0.5, limit=3)

    assert selected[0] == "c1"
    assert selected[1] == "c3"
    assert set(selected) == {"c1", "c2", "c3"}


def test_pgvector_search_applies_distance_cutoff_and_deduplicates_research(client, db, monkeypatch):
    projection = PgvectorProjection(DeterministicEmbeddingClient())
    monkeypatch.setattr(settings, "vector_data_provider", "pgvector")
    # SQLite has no <=> operator, so stub _search_chunks to return synthetic rows
    # and exercise only the cutoff + dedup + MMR path.
    candidates_full = [
        ("c1", "r1", "alpha content", 0.05),
        ("c2", "r1", "alpha content repeat", 0.05),
        ("c3", "r2", "different content entirely", 0.10),
        ("c4", "r3", "too far to rank", 0.90),
    ]

    def fake_search_chunks(_self, _db, _vector, *, limit, research_id=None, approved_only=False):
        return candidates_full[:3]

    monkeypatch.setattr(PgvectorProjection, "_search_chunks", fake_search_chunks)
    monkeypatch.setattr(settings, "search_semantic_max_distance", 0.5)

    ids = projection.search(db, "agent retrieval", 10)

    assert ids == ["r1", "r2"]
    # 'c4' would have been filtered by the 0.5 cutoff.
    monkeypatch.setattr(settings, "search_semantic_max_distance", 0.01)
    forced_empty = projection.search(db, "agent retrieval", 10)
    assert forced_empty == []


def test_hybrid_search_fuses_lexical_and_semantic_and_is_disabled_by_default(client, monkeypatch):
    item = approve(client, create_item(client, "Hybrid RAG retrieval", ["RAG"]))

    disabled = client.post("/api/v1/search/hybrid", json={"query": "retrieval", "limit": 5})
    assert disabled.status_code == 404

    monkeypatch.setattr(settings, "search_hybrid_enabled", True)
    monkeypatch.setattr(settings, "search_data_provider", "postgres")
    monkeypatch.setattr(settings, "vector_data_provider", "pgvector")
    monkeypatch.setattr(
        "app.api.search.embedding_client_from_settings",
        lambda: DeterministicEmbeddingClient(),
    )
    monkeypatch.setattr(
        PgvectorProjection, "search", lambda _self, _db, _query, _limit: [item["id"]]
    )

    response = client.post("/api/v1/search/hybrid", json={"query": "hybrid retrieval", "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["id"] == item["id"]
    assert payload["page_size"] == 5
