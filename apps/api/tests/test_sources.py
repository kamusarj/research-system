from pydantic import ValidationError

from app.schemas.graph import GraphMeta, GraphResponse
from app.services.ingestion import run_pending_submissions
from app.services.sources import detect_source_type, normalize_url
from app.services.sources.article import ArticleSourceAdapter
from app.services.sources.http import FetchedResource


def test_detects_supported_source_types():
    assert detect_source_type("https://github.com/langchain-ai/langgraph") == "github"
    assert detect_source_type("https://example.com/research/article") == "article"
    assert detect_source_type("https://www.facebook.com/reel/123456") == "facebook_reel"
    assert detect_source_type("https://example.com/paper.pdf?download=1") == "pdf"


def test_normalize_url_removes_tracking_and_fragment():
    assert normalize_url(
        "HTTPS://Example.COM:443/article/?utm_source=test&b=2&a=1#section"
    ) == "https://example.com/article?a=1&b=2"


def test_article_adapter_maps_to_normalized_source(monkeypatch):
    html = b"""
    <html lang="en"><head><title>Agent Evidence</title>
    <meta name="author" content="Research Team">
    <link rel="canonical" href="https://example.com/agent-evidence"></head>
    <body><nav>Noise</nav><article><h1>Findings</h1>
    <p>Grounded evidence for business agent evaluation with measurable outcomes.</p>
    </article><footer>Noise</footer></body></html>
    """
    monkeypatch.setattr(
        "app.services.sources.article.fetch_public",
        lambda *_: FetchedResource(
            final_url="https://example.com/original",
            content_type="text/html",
            content=html,
            encoding="utf-8",
        ),
    )

    source = ArticleSourceAdapter().collect("https://example.com/original")

    assert source.source_type == "article"
    assert source.canonical_url == "https://example.com/agent-evidence"
    assert source.title == "Agent Evidence"
    assert source.authors == ["Research Team"]
    assert "Noise" not in source.raw_text
    assert source.evidence


def test_facebook_reel_is_explicitly_waiting_for_transcript(client, db):
    response = client.post(
        "/api/v1/ingestion/links",
        json={"url": "https://www.facebook.com/reel/123456"},
    )
    assert response.status_code == 202
    assert run_pending_submissions(db) == 1
    submission = client.get("/api/v1/ingestion/links").json()[0]
    assert submission["status"] == "needs-transcript"
    assert submission["classification"]["normalized_source"]["collection_status"] == (
        "NEEDS_TRANSCRIPT"
    )


def test_graph_contract_rejects_duplicates_and_dangling_edges():
    duplicate_nodes = [
        {"id": "node:1", "type": "Concept", "label": "One"},
        {"id": "node:1", "type": "Concept", "label": "Duplicate"},
    ]
    try:
        GraphResponse(
            nodes=duplicate_nodes,
            edges=[],
            meta=GraphMeta(node_count=2, edge_count=0),
        )
    except ValidationError as exc:
        assert "duplicate node" in str(exc).casefold()
    else:
        raise AssertionError("Duplicate graph nodes must be rejected")

    try:
        GraphResponse(
            nodes=[{"id": "node:1", "type": "Concept", "label": "One"}],
            edges=[
                {
                    "id": "edge:1",
                    "source": "node:1",
                    "target": "missing",
                    "type": "RELATED_TO",
                }
            ],
            meta=GraphMeta(node_count=1, edge_count=1),
        )
    except ValidationError as exc:
        assert "missing node" in str(exc).casefold()
    else:
        raise AssertionError("Dangling graph edges must be rejected")


def test_graph_api_applies_hard_limit_and_keeps_unique_expansion(client):
    for index in range(4):
        created = client.post(
            "/api/v1/research",
            json={
                "title": f"Graph item {index}",
                "content": "Graph contract verification",
                "tags": [f"Concept {index}"],
            },
        ).json()
        client.post(f"/api/v1/research/{created['id']}/submit-review")
        client.post(f"/api/v1/research/{created['id']}/approve")

    graph = client.get("/api/v1/graph?limit=2").json()
    assert len(graph["nodes"]) == 2
    assert graph["meta"]["truncated"] is True
    root_id = graph["nodes"][0]["id"]
    expanded = client.get(f"/api/v1/graph/nodes/{root_id}/neighbors?limit=10").json()
    ids = [node["id"] for node in expanded["nodes"]]
    assert len(ids) == len(set(ids))
