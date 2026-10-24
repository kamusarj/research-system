import json
import subprocess
from datetime import UTC, datetime
from io import BytesIO

import httpx
import pytest
from PIL import Image
from pydantic import ValidationError
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.core.config import settings
from app.schemas.graph import GraphMeta, GraphResponse
from app.services.ocr import OCRPage, OCRResult, ocr_pdf
from app.services.sources import detect_source_type, normalize_url
from app.services.sources.article import ArticleSourceAdapter
from app.services.sources.base import RawSource
from app.services.sources.browser import BrowserRenderResult, _route_public_request
from app.services.sources.errors import SourceError
from app.services.sources.facebook import FacebookSourceAdapter
from app.services.sources.github import GitHubSourceAdapter, parse_github_target
from app.services.sources.http import (
    FetchedResource,
    assert_peer_is_public,
    fetch_public,
    resolve_encoding,
)
from app.services.sources.paper import PaperSourceAdapter
from app.services.sources.pdf import PDFSourceAdapter


def test_detects_supported_source_types():
    assert detect_source_type("https://github.com/langchain-ai/langgraph") == "github"
    assert detect_source_type("https://github.com/org/repo/issues/1") == "github"
    assert detect_source_type("https://www.facebook.com/posts/123456") == "facebook"
    assert detect_source_type("https://www.facebook.com/reel/123456") == "facebook"
    assert detect_source_type("https://fb.watch/abc") == "facebook"
    assert detect_source_type("https://arxiv.org/abs/2401.12345") == "paper"
    assert detect_source_type("https://doi.org/10.1000/example") == "paper"
    assert detect_source_type("https://ieeexplore.ieee.org/document/123") == "paper"
    assert detect_source_type("https://example.com/research/article") == "article"
    assert detect_source_type("https://example.com/download?id=2", "application/pdf") == "pdf"
    assert detect_source_type("https://example.com/paper.pdf?download=1") == "pdf"


def test_normalize_url_removes_tracking_fragment_and_default_port():
    assert (
        normalize_url("HTTPS://Example.COM:443/article/?utm_source=test&fbclid=x&b=2&a=1#section")
        == "https://example.com/article?a=1&b=2"
    )


def test_github_repository_file_issue_and_pull_targets():
    repository = parse_github_target("https://github.com/openai/codex")
    file = parse_github_target("https://github.com/openai/codex/blob/main/README.md")
    issue = parse_github_target("https://github.com/openai/codex/issues/42")
    pull = parse_github_target("https://github.com/openai/codex/pull/99")

    assert repository.kind == "repository"
    assert file.kind == "file" and file.path == "README.md" and file.ref == "main"
    assert issue.kind == "issue" and issue.number == 42
    assert pull.kind == "pull_request" and pull.number == 99


def test_github_repository_uses_exact_api_path_and_extracts_readme(monkeypatch):
    real_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/octocat/Hello-World":
            return httpx.Response(
                200,
                json={
                    "full_name": "octocat/Hello-World",
                    "description": "My first repository",
                    "default_branch": "master",
                    "language": "Python",
                    "topics": ["example"],
                    "owner": {"login": "octocat"},
                    "created_at": "2011-01-26T19:01:12Z",
                },
            )
        if path.endswith("/readme"):
            return httpx.Response(200, text="# Hello World\n\nA public example repository.")
        if path.endswith("/languages"):
            return httpx.Response(200, json={"Python": 100})
        if "/git/trees/" in path:
            return httpx.Response(200, json={"tree": [{"path": "README", "type": "blob"}]})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        "app.services.sources.github.httpx.Client",
        lambda **kwargs: real_client(
            transport=transport,
            base_url=kwargs.get("base_url"),
            headers=kwargs.get("headers"),
            timeout=kwargs.get("timeout"),
        ),
    )

    source = GitHubSourceAdapter().collect("https://github.com/octocat/Hello-World")

    assert source.title == "octocat/Hello-World"
    assert "public example repository" in source.raw_text
    assert source.metadata["primary_language"] == "Python"
    assert source.metadata["tree"][0]["path"] == "README"


def test_article_adapter_maps_to_normalized_source(monkeypatch):
    html = b"""
    <html lang="en"><head><title>Agent Evidence</title>
    <meta name="author" content="Research Team">
    <meta name="description" content="A careful research description.">
    <link rel="canonical" href="https://example.com/agent-evidence"></head>
    <body><nav>Noise</nav><article><h1>Findings</h1>
    <p>Grounded evidence for business agent evaluation with measurable outcomes.</p>
    <p>A second paragraph provides enough content for a complete extraction result.</p>
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
    assert source.description == "A careful research description."
    assert "Noise" not in source.raw_text
    assert source.collection_status == "EXTRACTED"
    assert source.evidence


def test_js_heavy_article_returns_useful_partial_result(monkeypatch):
    html = (
        b"<html><head><title>Client-rendered report</title>"
        b'<meta name="description" content="Metadata remains useful."></head>'
        b'<body><div id="root"></div></body></html>'
    )
    monkeypatch.setattr(
        "app.services.sources.article.fetch_public",
        lambda *_: FetchedResource(
            final_url="https://example.com/report",
            content_type="text/html",
            content=html,
            encoding="utf-8",
        ),
    )

    source = ArticleSourceAdapter().collect("https://example.com/report")

    assert source.collection_status == "PARTIAL"
    assert source.limitation_code == "JS_RENDER_REQUIRED"
    assert source.description == "Metadata remains useful."


def test_facebook_post_and_reel_return_bounded_metadata(monkeypatch):
    html = b"""
    <meta property="og:url" content="https://www.facebook.com/example/posts/123">
    <meta property="og:title" content="Public research update">
    <meta property="og:description" content="Public summary available without login.">
    <meta property="og:image" content="https://cdn.example.com/preview.jpg">
    """
    monkeypatch.setattr(
        "app.services.sources.facebook.fetch_public",
        lambda *_args, **_kwargs: FetchedResource(
            final_url="https://www.facebook.com/example/posts/123",
            content_type="text/html",
            content=html,
            encoding="utf-8",
        ),
    )

    source = FacebookSourceAdapter().collect("https://fb.watch/shared")

    assert source.source_type == "facebook"
    assert source.metadata["resource_kind"] == "post"
    assert source.collection_status == "PARTIAL"
    assert source.limitation_code == "METADATA_ONLY"
    assert source.media[0].type == "image"


def test_fb_watch_redirect_is_followed_and_revalidated(monkeypatch):
    real_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "fb.watch":
            return httpx.Response(
                302,
                headers={"location": "https://www.facebook.com/reel/123"},
                request=request,
            )
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b'<meta property="og:title" content="Public reel">',
            request=request,
        )

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr("app.services.sources.http.validate_public_url", lambda _url: None)
    monkeypatch.setattr(
        "app.services.sources.http.httpx.Client",
        lambda **kwargs: real_client(
            transport=transport,
            follow_redirects=kwargs.get("follow_redirects", False),
            timeout=kwargs.get("timeout"),
        ),
    )

    resource = fetch_public("https://fb.watch/shared", {"text/html"})

    assert resource.final_url == "https://www.facebook.com/reel/123"
    assert b"Public reel" in resource.content


def _mock_fetch(monkeypatch, handler):
    """Point ``fetch_public`` at a scripted transport without touching the network."""

    real_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr("app.services.sources.http.validate_public_url", lambda _url: None)
    monkeypatch.setattr(
        "app.services.sources.http.httpx.Client",
        lambda **kwargs: real_client(
            transport=transport,
            follow_redirects=kwargs.get("follow_redirects", False),
            timeout=kwargs.get("timeout"),
        ),
    )


def test_requests_identify_as_a_browser_and_accept_vietnamese(monkeypatch):
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        return httpx.Response(
            200, headers={"content-type": "text/html"}, content=b"<p>ok</p>", request=request
        )

    _mock_fetch(monkeypatch, handler)

    fetch_public("https://publisher.example/article", {"text/html"})

    assert "Mozilla/5.0" in seen["user-agent"]
    assert "ResearchSystem" not in seen["user-agent"]
    assert seen["accept-language"].startswith("vi")


def test_per_host_headers_override_the_browser_defaults(monkeypatch):
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        return httpx.Response(
            200, headers={"content-type": "text/html"}, content=b"<p>ok</p>", request=request
        )

    _mock_fetch(monkeypatch, handler)
    monkeypatch.setattr(
        settings, "intake_host_headers", {"publisher.example": {"Accept-Language": "en-GB"}}
    )

    fetch_public("https://www.publisher.example/article", {"text/html"})

    assert seen["accept-language"] == "en-GB"


def test_content_type_aliases_and_families_are_accepted(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/xhtml+xml; charset=utf-8"},
            content=b"<p>xhtml body</p>",
            request=request,
        )

    _mock_fetch(monkeypatch, handler)

    resource = fetch_public("https://publisher.example/article", {"text/html"})

    assert resource.content_type == "application/xhtml+xml"
    assert b"xhtml body" in resource.content


def test_unsupported_content_type_is_refused_before_the_body_is_downloaded(monkeypatch):
    downloaded = []

    def handler(request: httpx.Request) -> httpx.Response:
        downloaded.append(request.url.path)
        return httpx.Response(
            200,
            headers={"content-type": "video/mp4", "content-length": "999999"},
            content=b"\x00" * 64,
            request=request,
        )

    _mock_fetch(monkeypatch, handler)

    with pytest.raises(SourceError) as failure:
        fetch_public("https://publisher.example/clip", {"text/html"})

    assert failure.value.code == "UNSUPPORTED_CONTENT_TYPE"
    assert failure.value.details["content_type"] == "video/mp4"


def test_bot_challenge_pages_are_reported_as_bot_protection(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"<html><title>Just a moment...</title>"
            b"<div id='cf-browser-verification'></div></html>",
            request=request,
        )

    _mock_fetch(monkeypatch, handler)

    with pytest.raises(SourceError) as failure:
        fetch_public("https://publisher.example/article", {"text/html"})

    assert failure.value.code == "BOT_PROTECTED"


def test_a_plain_refusal_behind_cloudflare_is_still_reported_as_bot_protection(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            headers={"content-type": "text/html", "server": "cloudflare"},
            content=b"<html>error 1020</html>",
            request=request,
        )

    _mock_fetch(monkeypatch, handler)

    with pytest.raises(SourceError) as failure:
        fetch_public("https://publisher.example/article", {"text/html"})

    assert failure.value.code == "BOT_PROTECTED"


def test_a_healthy_page_served_by_cloudflare_is_not_treated_as_a_challenge(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html", "server": "cloudflare"},
            content=b"<html><p>A real article behind a normal CDN.</p></html>",
            request=request,
        )

    _mock_fetch(monkeypatch, handler)

    resource = fetch_public("https://publisher.example/article", {"text/html"})

    assert b"A real article" in resource.content


def test_server_errors_are_left_for_the_worker_to_reschedule(monkeypatch):
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(request.url.path)
        return httpx.Response(503, headers={"content-type": "text/html"}, request=request)

    _mock_fetch(monkeypatch, handler)

    with pytest.raises(SourceError) as failure:
        fetch_public("https://publisher.example/article", {"text/html"})

    # One attempt only: retrying here as well as in the worker multiplies the load on a
    # site that has already said it is struggling.
    assert len(attempts) == 1
    assert failure.value.code == "FETCH_FAILED"
    assert failure.value.retryable is True


def test_a_legacy_page_decodes_from_the_declared_meta_charset(monkeypatch):
    body = '<meta charset="windows-1252"><p>Café Résumé Année</p>'.encode("windows-1252")

    def handler(request: httpx.Request) -> httpx.Response:
        # No charset in the header: the declaration inside the document is all there is.
        return httpx.Response(
            200, headers={"content-type": "text/html"}, content=body, request=request
        )

    _mock_fetch(monkeypatch, handler)

    resource = fetch_public("https://publisher.example/legacy", {"text/html"})

    assert resource.encoding == "windows-1252"
    assert "Café Résumé Année" in resource.content.decode(resource.encoding)


def test_vietnamese_utf8_pages_survive_a_missing_charset_declaration(monkeypatch):
    body = "<p>Trí tuệ nhân tạo cho doanh nghiệp</p>".encode()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"content-type": "text/html"}, content=body, request=request
        )

    _mock_fetch(monkeypatch, handler)

    resource = fetch_public("https://publisher.example/vi", {"text/html"})

    assert "Trí tuệ nhân tạo cho doanh nghiệp" in resource.content.decode(resource.encoding)


def test_encoding_resolution_prefers_a_header_that_actually_decodes():
    utf8 = "Trí tuệ".encode()

    assert resolve_encoding(utf8, "utf-8") == "utf-8"
    # A header charset the bytes do not honour is discarded rather than trusted.
    assert resolve_encoding(utf8, "ascii") == "utf-8"
    assert resolve_encoding(utf8, "definitely-not-a-charset") == "utf-8"


def test_a_connection_that_lands_on_a_private_address_is_refused():
    class PrivatePeerStream:
        def get_extra_info(self, name: str):
            return ("10.0.0.5", 443) if name == "server_addr" else None

    response = httpx.Response(200, extensions={"network_stream": PrivatePeerStream()})

    with pytest.raises(SourceError) as failure:
        assert_peer_is_public(response)

    assert failure.value.code == "INVALID_URL"


def test_a_connection_that_lands_on_a_public_address_is_allowed():
    class PublicPeerStream:
        def get_extra_info(self, name: str):
            return ("93.184.216.34", 443) if name == "server_addr" else None

    assert_peer_is_public(httpx.Response(200, extensions={"network_stream": PublicPeerStream()}))


def test_arxiv_metadata_extracts_authors_abstract_and_pdf():
    atom = b"""
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry><title>Reliable Agents</title><summary>An evidence-backed abstract.</summary>
      <published>2026-01-02T00:00:00Z</published><author><name>Ada Researcher</name></author>
      <arxiv:doi>10.1000/example</arxiv:doi></entry>
    </feed>
    """
    source = PaperSourceAdapter().extract(
        RawSource(
            requested_url="https://arxiv.org/abs/2601.00001",
            final_url="https://arxiv.org/abs/2601.00001",
            content_type="application/atom+xml",
            content=atom,
            metadata={"provider": "arxiv", "arxiv_id": "2601.00001"},
        )
    )

    assert source.title == "Reliable Agents"
    assert source.authors == ["Ada Researcher"]
    assert source.published_at == datetime(2026, 1, 2, tzinfo=UTC)
    assert source.metadata["doi"] == "10.1000/example"
    assert source.media[0].url.endswith("2601.00001.pdf")


def test_doi_metadata_without_abstract_is_partial_not_empty_success():
    payload = {
        "message": {
            "DOI": "10.1000/example",
            "title": ["Structured research"],
            "author": [{"given": "Lin", "family": "Nguyen"}],
            "published": {"date-parts": [[2026, 2, 3]]},
            "publisher": "Example Press",
        }
    }
    source = PaperSourceAdapter().extract(
        RawSource(
            requested_url="https://doi.org/10.1000/example",
            final_url="https://doi.org/10.1000/example",
            content_type="application/vnd.crossref+json",
            content=json.dumps(payload).encode(),
            metadata={"provider": "crossref", "doi": "10.1000/example"},
        )
    )

    assert source.title == "Structured research"
    assert source.collection_status == "PARTIAL"
    assert source.limitation_code == "ABSTRACT_UNAVAILABLE"
    assert source.raw_text == "Structured research"


def test_doi_falls_back_to_registry_neutral_csl_metadata(monkeypatch):
    def crossref_not_found(_url: str):
        raise SourceError("SOURCE_NOT_FOUND", "Paper metadata was not found")

    monkeypatch.setattr("app.services.sources.paper._api_json", crossref_not_found)
    monkeypatch.setattr(
        "app.services.sources.paper.fetch_public",
        lambda *_args, **_kwargs: FetchedResource(
            final_url="https://data.crosscite.org/10.48550/arXiv.1706.03762",
            content_type="application/vnd.citationstyles.csl+json",
            content=json.dumps(
                {
                    "DOI": "10.48550/arXiv.1706.03762",
                    "title": "Attention Is All You Need",
                    "author": [{"given": "Ashish", "family": "Vaswani"}],
                    "abstract": "A transformer architecture for sequence modeling.",
                    "issued": {"date-parts": [[2017, 6, 12]]},
                    "publisher": "arXiv",
                    "type": "article",
                    "URL": "https://arxiv.org/abs/1706.03762",
                }
            ).encode(),
            encoding="utf-8",
        ),
    )

    source = PaperSourceAdapter().collect("https://doi.org/10.48550/arXiv.1706.03762")

    assert source.title == "Attention Is All You Need"
    assert source.canonical_url == "https://doi.org/10.48550/arXiv.1706.03762"
    assert source.authors == ["Ashish Vaswani"]
    assert source.metadata["provider"] == "doi_csl"
    assert source.metadata["pdf_url"] == "https://arxiv.org/pdf/1706.03762.pdf"
    assert source.collection_status == "EXTRACTED"


def test_scanned_pdf_is_reported_as_partial(monkeypatch):
    class Page:
        def extract_text(self):
            return ""

    class Reader:
        pages = [Page(), Page()]
        metadata = {"/Title": "Scanned evidence"}

    monkeypatch.setattr("app.services.sources.pdf.PdfReader", lambda *_args, **_kwargs: Reader())
    source = PDFSourceAdapter().extract(
        RawSource(
            requested_url="https://example.com/paper.pdf",
            final_url="https://example.com/paper.pdf",
            content_type="application/pdf",
            content=b"%PDF-scanned",
        )
    )

    assert source.collection_status == "PARTIAL"
    assert source.limitation_code == "PDF_SCANNED_OCR_DISABLED"
    assert source.metadata["has_text_layer"] is False


def test_bounded_ocr_uses_memory_pipe_and_page_budget(monkeypatch):
    class Bitmap:
        def to_pil(self):
            return Image.new("RGB", (20, 20), "white")

    class Page:
        def get_size(self):
            return 72, 72

        def render(self, scale):
            assert scale == 200 / 72
            return Bitmap()

    class Document:
        def __len__(self):
            return 3

        def __getitem__(self, _index):
            return Page()

        def close(self):
            pass

    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=b"Grounded OCR evidence with enough readable text for review.",
            stderr=b"private diagnostic marker",
        )

    monkeypatch.setattr("app.services.ocr.pdfium.PdfDocument", lambda _content: Document())
    monkeypatch.setattr("app.services.ocr.subprocess.run", run)
    monkeypatch.setattr("app.services.ocr.settings.ocr_enabled", True)
    monkeypatch.setattr("app.services.ocr.settings.ocr_max_pages", 2)
    monkeypatch.setattr("app.services.ocr.settings.ocr_min_chars", 10)

    result = ocr_pdf(b"%PDF-scanned")

    assert len(result.pages) == 2
    assert result.limitation_code == "OCR_PAGE_LIMIT"
    assert all(call[0][:3] == ["tesseract", "stdin", "stdout"] for call in calls)
    assert all(call[1]["input"].startswith(b"\x89PNG") for call in calls)
    assert all("private diagnostic marker" not in page.text for page in result.pages)


def test_pdf_adapter_uses_ocr_with_page_provenance(monkeypatch):
    class Page:
        def extract_text(self):
            return ""

    class Reader:
        pages = [Page()]
        metadata = {"/Title": "Scanned evidence"}

    monkeypatch.setattr("app.services.sources.pdf.PdfReader", lambda *_args, **_kwargs: Reader())
    monkeypatch.setattr(
        "app.services.sources.pdf.ocr_pdf",
        lambda _content: OCRResult(
            pages=[OCRPage(page=1, text="OCR evidence recovered from the scanned page.")],
            total_pages=1,
            pages_attempted=1,
        ),
    )
    source = PDFSourceAdapter().extract(
        RawSource(
            requested_url="https://example.com/scan.pdf",
            final_url="https://example.com/scan.pdf",
            content_type="application/pdf",
            content=b"%PDF-scanned",
        )
    )

    assert source.collection_status == "EXTRACTED"
    assert source.metadata["has_text_layer"] is False
    assert source.metadata["ocr_applied"] is True
    assert source.evidence[0].page == 1


def test_browser_route_blocks_heavy_and_non_public_requests(monkeypatch):
    class Request:
        def __init__(self, url, resource_type="document"):
            self.url = url
            self.resource_type = resource_type

    class Route:
        def __init__(self, request):
            self.request = request
            self.action = None

        def abort(self):
            self.action = "abort"

        def continue_(self):
            self.action = "continue"

    def validate(url):
        if "127.0.0.1" in url:
            raise SourceError("INVALID_URL", "Private URL")

    monkeypatch.setattr("app.services.sources.browser.validate_public_url", validate)
    counters = {"request_count": 0, "blocked_count": 0}
    public = Route(Request("https://example.com/app.js", "script"))
    private = Route(Request("http://127.0.0.1/admin"))
    image = Route(Request("https://example.com/large.png", "image"))

    for route in (public, private, image):
        _route_public_request(route, counters)

    assert public.action == "continue"
    assert private.action == image.action == "abort"
    assert counters == {"request_count": 3, "blocked_count": 2}


def test_js_article_uses_browser_fallback_only_when_enabled(monkeypatch):
    initial = RawSource(
        requested_url="https://example.com/app",
        final_url="https://example.com/app",
        content_type="text/html",
        content=b"<title>Rendered report</title><div id='root'></div>",
    )
    rendered = RawSource(
        requested_url="https://example.com/app",
        final_url="https://example.com/app",
        content_type="text/html",
        content=(
            b"<title>Rendered report</title><article><p>Grounded browser-rendered evidence "
            b"for a governed business agent workflow with human review and measurable outcomes."
            b"</p></article>"
        ),
    )
    adapter = ArticleSourceAdapter()
    monkeypatch.setattr(adapter, "fetch", lambda _url: initial)
    monkeypatch.setattr("app.services.ingestion.adapter_for_url", lambda *_args: adapter)
    monkeypatch.setattr("app.services.ingestion.settings.browser_render_enabled", True)
    monkeypatch.setattr(
        "app.services.ingestion.render_public_article",
        lambda _url: BrowserRenderResult(raw=rendered, request_count=3, blocked_count=1),
    )

    from app.services.ingestion import fetch_url

    source = fetch_url("https://example.com/app").normalized

    assert source.collection_status == "EXTRACTED"
    assert source.metadata["browser_rendered"] is True
    assert source.metadata["browser_request_count"] == 3


def test_direct_pdf_text_layer_is_extracted():
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 12 Tf 72 720 Td (Business agent evaluation evidence and findings.) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = BytesIO()
    writer.write(buffer)

    source = PDFSourceAdapter().extract(
        RawSource(
            requested_url="https://example.com/evidence.pdf",
            final_url="https://example.com/evidence.pdf",
            content_type="application/pdf",
            content=buffer.getvalue(),
        )
    )

    assert source.collection_status == "EXTRACTED"
    assert "Business agent evaluation evidence" in source.raw_text
    assert source.metadata["has_text_layer"] is True


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
