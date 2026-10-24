from app.services.sources.article import ArticleSourceAdapter
from app.services.sources.base import RawSource
from app.services.sources.quality import assess_article

ARTICLE_BODY = (
    "Governed business agents need measurable outcomes before they reach production, "
    "and every claim in this report is backed by an evaluation run that a reviewer can "
    "reproduce from the recorded inputs."
)


def _html(body: str, *, title: str = "Report") -> RawSource:
    return RawSource(
        requested_url="https://publisher.example/report",
        final_url="https://publisher.example/report",
        content_type="text/html",
        content=f"<html><head><title>{title}</title></head><body>{body}</body></html>".encode(),
        encoding="utf-8",
    )


def test_real_article_prose_is_accepted():
    quality = assess_article(ARTICLE_BODY)

    assert quality.complete is True
    assert quality.collection_status == "EXTRACTED"
    assert quality.limitation_code is None


def test_a_cookie_notice_is_named_rather_than_stored_as_the_article():
    quality = assess_article("We use cookies to improve your experience. Accept all cookies")

    assert quality.complete is False
    assert quality.limitation_code == "CONSENT_WALL"


def test_a_vietnamese_cookie_notice_is_recognised():
    quality = assess_article("Chúng tôi sử dụng cookie để cải thiện trải nghiệm của bạn.")

    assert quality.limitation_code == "CONSENT_WALL"


def test_a_subscription_gate_is_named_as_a_paywall():
    quality = assess_article("Subscribe to continue reading. Already a subscriber? Sign in.")

    assert quality.limitation_code == "PAYWALL"


def test_a_full_article_that_merely_mentions_cookies_is_still_complete():
    quality = assess_article(f"{ARTICLE_BODY}\n\nWe use cookies to remember your preferences.")

    assert quality.complete is True


def test_an_empty_shell_is_reported_as_needing_javascript():
    quality = assess_article("", has_metadata=True)

    assert quality.limitation_code == "JS_RENDER_REQUIRED"
    assert "metadata" in quality.limitation_message


def test_a_shell_without_metadata_says_so_plainly():
    quality = assess_article("", has_metadata=False)

    assert quality.limitation_code == "JS_RENDER_REQUIRED"
    assert "no readable article body" in quality.limitation_message


def test_the_article_adapter_reports_a_consent_wall_end_to_end():
    source = ArticleSourceAdapter().extract(
        _html("<p>We use cookies and similar technologies. Accept all cookies to continue.</p>")
    )

    assert source.collection_status == "PARTIAL"
    assert source.limitation_code == "CONSENT_WALL"


def test_the_article_adapter_records_what_it_measured():
    source = ArticleSourceAdapter().extract(_html(f"<article><p>{ARTICLE_BODY}</p></article>"))

    assert source.collection_status == "EXTRACTED"
    assert source.metadata["extracted_chars"] > 0
    assert source.metadata["js_render_suspected"] is False
