"""Judge whether an extraction actually captured the article.

A page that answers with HTTP 200 has not necessarily given up its content. Cookie
banners, subscription gates and client-rendered shells all return a healthy status and a
body that looks like a document. Treating those as successful extractions is what puts
empty records into the knowledge graph, so each one is named instead.
"""

from dataclasses import dataclass

# Enough prose that length alone settles it, whatever the page structure looks like.
MIN_ARTICLE_CHARS = 400
# Below this a page is a shell, a redirect notice or a nav bar, never an article.
MIN_ANY_CHARS = 100
# One continuous run of prose this long is the shortest thing that reads as body text
# rather than a headline, caption or button label.
MIN_PROSE_BLOCK_CHARS = 80
# A paragraph shorter than this is not worth quoting as evidence.
MIN_PARAGRAPH_CHARS = 40

CONSENT_MARKERS = (
    "accept all cookies",
    "we use cookies",
    "manage your cookie",
    "cookie preferences",
    "consent to the use of cookies",
    "your privacy choices",
    "chấp nhận tất cả cookie",
    "chúng tôi sử dụng cookie",
    "quản lý tuỳ chọn cookie",
    "quản lý tùy chọn cookie",
)

PAYWALL_MARKERS = (
    "subscribe to continue",
    "subscribe to read",
    "this article is for subscribers",
    "already a subscriber",
    "create a free account to continue",
    "register to continue reading",
    "unlock this article",
    "đăng ký để đọc tiếp",
    "nội dung dành cho người đăng ký",
    "vui lòng đăng nhập để đọc",
)


@dataclass(slots=True)
class ContentQuality:
    """The verdict on one extraction, ready to become a limitation on the source."""

    complete: bool
    limitation_code: str | None = None
    limitation_message: str | None = None

    @property
    def collection_status(self) -> str:
        return "EXTRACTED" if self.complete else "PARTIAL"


def meaningful_paragraphs(text: str) -> list[str]:
    return [
        part.strip()
        for part in text.split("\n\n")
        if len(part.strip()) >= MIN_PARAGRAPH_CHARS
    ]


def _contains_any(haystack: str, markers: tuple[str, ...]) -> bool:
    return any(marker in haystack for marker in markers)


def assess_article(text: str, *, has_metadata: bool = False) -> ContentQuality:
    """Decide whether extracted article text is the article or a stand-in for it.

    ``has_metadata`` records that a title or description survived, which is the difference
    between "we got the summary but not the body" and "we got nothing at all".
    """

    stripped = text.strip()
    lowered = stripped.casefold()
    longest_block = max((len(block) for block in stripped.split("\n\n")), default=0)
    substantial = len(stripped) >= MIN_ARTICLE_CHARS or (
        len(stripped) >= MIN_ANY_CHARS and longest_block >= MIN_PROSE_BLOCK_CHARS
    )

    if _contains_any(lowered, PAYWALL_MARKERS) and not substantial:
        return ContentQuality(
            complete=False,
            limitation_code="PAYWALL",
            limitation_message=(
                "Only the public preview was returned; the article body is behind a paywall."
            ),
        )
    if _contains_any(lowered, CONSENT_MARKERS) and not substantial:
        return ContentQuality(
            complete=False,
            limitation_code="CONSENT_WALL",
            limitation_message=(
                "A cookie or privacy notice was returned in place of the article body."
            ),
        )
    if not substantial:
        return ContentQuality(
            complete=False,
            limitation_code="JS_RENDER_REQUIRED",
            limitation_message=(
                "Only page metadata was available; the main content may require JavaScript."
                if has_metadata
                else "The page returned no readable article body."
            ),
        )
    return ContentQuality(complete=True)
