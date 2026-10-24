"""The decisions the Discord adapter makes, with no Discord or network in sight.

The bot is a gateway: it recognises what a message carries, decides whether it is allowed
to act, builds the receipt the API expects, and turns the API's answer back into something
a person reads in a channel. Every rule about extraction, classification and the knowledge
graph stays in the API and worker (DEC-028), so nothing here interprets a source.

Keeping this module free of `discord` imports is what makes those rules testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

# Discord wraps suppressed links in angle brackets and often trails punctuation onto a
# URL, so the match is deliberately conservative and trimmed afterwards.
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
TRAILING_PUNCTUATION = ".,;:!?)]}'\"" + "”’"

# One message should not be able to enqueue unbounded work. The API caps a receipt at 20
# items; this bounds it earlier so the surplus can be reported rather than silently cut.
MAX_URLS_PER_MESSAGE = 20
MAX_ATTACHMENTS_PER_MESSAGE = 5
MAX_ATTACHMENT_BYTES = 20_000_000
PDF_CONTENT_TYPES = {"application/pdf", "application/x-pdf", "application/acrobat"}


@dataclass(frozen=True, slots=True)
class Attachment:
    """A Discord attachment, reduced to what the gateway needs to decide about it."""

    id: str
    filename: str
    content_type: str | None
    size: int
    url: str


@dataclass(frozen=True, slots=True)
class IncomingMessage:
    id: str
    channel_id: str
    guild_id: str | None
    author_id: str
    author_is_bot: bool
    content: str
    attachments: tuple[Attachment, ...] = ()


@dataclass(slots=True)
class MessagePlan:
    """What the gateway will do about one message, and what it refuses to do."""

    urls: list[str] = field(default_factory=list)
    documents: list[Attachment] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def actionable(self) -> bool:
        return bool(self.urls or self.documents)


@dataclass(frozen=True, slots=True)
class Allowlist:
    """Where the bot is permitted to listen.

    An empty guild or channel set means "nowhere", not "everywhere". A gateway that
    defaults to open would collect from any server it is invited to.
    """

    guild_ids: frozenset[str] = frozenset()
    channel_ids: frozenset[str] = frozenset()

    def permits(self, message: IncomingMessage) -> bool:
        if message.author_is_bot:
            return False
        if message.guild_id is None or message.guild_id not in self.guild_ids:
            return False
        return message.channel_id in self.channel_ids


def extract_urls(content: str) -> list[str]:
    """Pull every distinct public URL out of a message, in the order they were written."""

    seen: dict[str, str] = {}
    for match in URL_PATTERN.finditer(content or ""):
        url = match.group(0).rstrip(TRAILING_PUNCTUATION)
        if len(url) < 12:
            continue
        seen.setdefault(url.casefold(), url)
    return list(seen.values())


def is_supported_document(attachment: Attachment) -> bool:
    content_type = (attachment.content_type or "").split(";", 1)[0].strip().casefold()
    if content_type in PDF_CONTENT_TYPES:
        return True
    # Discord omits the content type for some clients, so the extension is the fallback.
    return not content_type and attachment.filename.casefold().endswith(".pdf")


def plan_message(message: IncomingMessage) -> MessagePlan:
    """Decide what one message contributes, and say what was left out and why."""

    plan = MessagePlan()
    urls = extract_urls(message.content)
    if len(urls) > MAX_URLS_PER_MESSAGE:
        plan.skipped.append(
            f"chỉ nhận {MAX_URLS_PER_MESSAGE} liên kết đầu tiên trong tổng số {len(urls)} liên kết"
        )
    plan.urls = urls[:MAX_URLS_PER_MESSAGE]

    for attachment in message.attachments:
        if not is_supported_document(attachment):
            plan.skipped.append(f"{attachment.filename}: hệ thống chỉ thu thập tệp PDF đính kèm")
            continue
        if attachment.size > MAX_ATTACHMENT_BYTES:
            plan.skipped.append(f"{attachment.filename}: vượt giới hạn 20 MB")
            continue
        if len(plan.documents) >= MAX_ATTACHMENTS_PER_MESSAGE:
            plan.skipped.append(
                f"{attachment.filename}: vượt giới hạn "
                f"{MAX_ATTACHMENTS_PER_MESSAGE} tệp trong một tin nhắn"
            )
            continue
        plan.documents.append(attachment)
    return plan


def receipt_payload(
    message: IncomingMessage,
    plan: MessagePlan,
    *,
    namespace: str,
    provider: str | None = None,
    auto_approve: bool = True,
) -> dict:
    """Build the receipt body.

    ``occurrence_ref`` is the Discord message ID. Paired with each item's normalized URL
    on the API side, that is what makes a replayed or edited message idempotent without
    losing the fact that the same source was seen twice.
    """

    return {
        "source": {
            "type": "discord",
            "namespace": namespace,
            "occurrence_ref": message.id,
            "container_ref": message.channel_id,
            "external_actor_ref": message.author_id,
            "metadata": {"schema_version": 1, "event_type": "message"},
        },
        "items": [
            {
                "kind": "url",
                "url": url,
                "auto_approve": auto_approve,
                **({"provider": provider} if provider else {}),
            }
            for url in plan.urls
        ],
    }


def document_item_ref(message: IncomingMessage, attachment: Attachment) -> str:
    """Identify one attachment across replays of the same message."""

    return f"{message.id}:{attachment.id}"


ItemOutcome = Literal["working", "published", "needs_review", "partial", "duplicate", "failed"]

# Terminal states, so the poller knows when to stop asking.
SETTLED_OUTCOMES: frozenset[str] = frozenset(
    {"published", "needs_review", "partial", "duplicate", "failed"}
)

OUTCOME_REACTIONS: dict[str, str] = {
    "working": "⏳",
    "published": "✅",
    "needs_review": "📥",
    "partial": "⚠️",
    "duplicate": "♻️",
    "failed": "❌",
}


def item_outcome(item: dict) -> ItemOutcome:
    """Reduce one receipt item to the single thing a reader in a channel cares about."""

    status = str(item.get("status") or "")
    review_status = str(item.get("review_status") or "")
    if item.get("disposition") == "linked_existing" or review_status == "duplicate":
        return "duplicate"
    if status == "failed":
        return "failed"
    if review_status == "approved":
        return "published"
    if status == "partial_success":
        return "partial"
    if status in {"completed", "needs_review"}:
        return "needs_review"
    return "working"


def receipt_outcome(receipt: dict) -> ItemOutcome:
    """Summarise a whole receipt by its least happy item, so nothing hides behind a tick."""

    outcomes = [item_outcome(item) for item in receipt.get("items", [])]
    if not outcomes:
        return "working"
    for candidate in ("failed", "partial", "working", "needs_review", "duplicate", "published"):
        if candidate in outcomes:
            return candidate  # type: ignore[return-value]
    return "working"


def receipt_settled(receipt: dict) -> bool:
    items = receipt.get("items", [])
    return bool(items) and all(item_outcome(item) in SETTLED_OUTCOMES for item in items)
