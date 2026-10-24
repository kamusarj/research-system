from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

import httpx

from app.core.config import settings
from app.services.object_storage import DocumentError, ObjectStorage
from app.services.sources.errors import SourceError
from app.services.sources.http import (
    DEFAULT_USER_AGENT,
    assert_peer_is_public,
    normalize_content_type,
    validate_public_url,
)

SHARE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
SEDIMENT_IMAGE_PATTERN = re.compile(
    r"^sediment://(?P<file_id>file_[0-9a-fA-F]{16,128})"
    r"(?:/[^?#]*)?(?:\?shared_conversation_id=[A-Za-z0-9_-]{16,128})?$"
)
PRIVATE_USE_PATTERN = re.compile("[\uE000-\uF8FF]")
CITATION_TOKEN_PATTERN = re.compile(r"\s*(?:citeturn|navlist|turn\d+\w*)[^,\s]*,?")
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
SKIPPED_CONTENT_TYPES = {"thoughts", "reasoning_recap", "model_editable_context", "tool_response"}
ALLOWED_IMAGE_HOST_SUFFIXES = (
    "oaiusercontent.com",
    "oaistatic.com",
    "chatgpt.com",
    "openai.com",
)
ALLOWED_IMAGE_EXACT_HOSTS = {"oaidalleapiprodscus.blob.core.windows.net"}
ALLOWED_IMAGE_TYPES = {
    "image/avif": "avif",
    "image/gif": "gif",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


@dataclass(frozen=True, slots=True)
class ImportedChatMedia:
    type: str
    url: str
    alt: str
    storage_key: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None


@dataclass(frozen=True, slots=True)
class ImportedChatMessage:
    role: str
    content: str
    created_at: datetime | None = None
    media: tuple[ImportedChatMedia, ...] = ()


@dataclass(frozen=True, slots=True)
class ChatGPTSharedSnapshot:
    title: str
    messages: tuple[ImportedChatMessage, ...]
    canonical_url: str
    snapshot_hash: str
    total_characters: int
    stored_object_keys: tuple[str, ...] = ()


class _ScriptCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_script = False
        self._attrs: dict[str, str] = {}
        self._data: list[str] = []
        self.scripts: list[tuple[dict[str, str], str]] = []

    def handle_starttag(
        self, tag: str, attrs: Sequence[tuple[str, str | None]]
    ) -> None:
        if tag.casefold() != "script":
            return
        self._in_script = True
        self._attrs = {name: value or "" for name, value in attrs}
        self._data = []

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() != "script" or not self._in_script:
            return
        self.scripts.append((self._attrs, "".join(self._data)))
        self._in_script = False
        self._attrs = {}
        self._data = []

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self._data.append(data)


def _scripts(html: str) -> list[tuple[dict[str, str], str]]:
    parser = _ScriptCollector()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:
        raise DocumentError(
            "CHAT_IMPORT_PARSE_FAILED", "The shared conversation page is not valid HTML", 422
        ) from exc
    return parser.scripts


def validate_chatgpt_share_url(value: str) -> str:
    try:
        parsed = urlparse(value.strip())
        port = parsed.port
    except ValueError as exc:
        raise DocumentError(
            "CHAT_IMPORT_URL_INVALID", "The ChatGPT shared link is malformed", 422
        ) from exc
    path_parts = [part for part in parsed.path.split("/") if part]
    if (
        parsed.scheme != "https"
        or (parsed.hostname or "").casefold().rstrip(".") != "chatgpt.com"
        or port is not None
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or len(path_parts) != 2
        or path_parts[0] != "share"
        or not SHARE_ID_PATTERN.fullmatch(path_parts[1])
    ):
        raise DocumentError(
            "CHAT_IMPORT_URL_INVALID",
            "Use a public https://chatgpt.com/share/<conversation-id> link",
            422,
        )
    return urlunparse(("https", "chatgpt.com", f"/share/{path_parts[1]}", "", "", ""))


def _fetch_share_html(url: str, client: httpx.Client | None = None) -> tuple[str, str]:
    current_url = validate_chatgpt_share_url(url)
    redirects = 0
    headers = {
        "User-Agent": settings.intake_user_agent or DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml;q=0.9",
        "Accept-Language": settings.intake_accept_language,
        "Accept-Encoding": "gzip, deflate",
        "Referer": "https://chatgpt.com/",
        "Cache-Control": "no-cache",
    }
    owned_client = client is None
    client = client or httpx.Client(
        follow_redirects=False,
        timeout=httpx.Timeout(settings.chat_import_timeout_seconds),
    )
    try:
        while True:
            validate_public_url(current_url)
            with client.stream("GET", current_url, headers=headers) as response:
                assert_peer_is_public(response)
                if response.status_code in REDIRECT_STATUSES:
                    location = response.headers.get("location")
                    if not location:
                        raise DocumentError(
                            "CHAT_IMPORT_UNAVAILABLE",
                            "The shared conversation returned an invalid redirect",
                            502,
                        )
                    redirects += 1
                    if redirects > settings.chat_import_max_redirects:
                        raise DocumentError(
                            "CHAT_IMPORT_UNAVAILABLE",
                            "The shared conversation redirected too many times",
                            502,
                        )
                    current_url = validate_chatgpt_share_url(urljoin(current_url, location))
                    continue
                if response.status_code in {404, 410}:
                    raise DocumentError(
                        "CHAT_IMPORT_NOT_FOUND",
                        "The shared conversation is unavailable or has been deleted",
                        404,
                    )
                if response.status_code >= 400:
                    raise DocumentError(
                        "CHAT_IMPORT_UNAVAILABLE",
                        "ChatGPT did not return the public shared conversation",
                        502,
                    )
                content_type = normalize_content_type(response.headers.get("content-type"))
                if content_type not in {"text/html", "application/xhtml+xml", ""}:
                    raise DocumentError(
                        "CHAT_IMPORT_UNSUPPORTED",
                        "The shared link did not return an HTML conversation snapshot",
                        415,
                    )
                declared = response.headers.get("content-length")
                if (
                    declared
                    and declared.isdigit()
                    and int(declared) > settings.chat_import_max_html_bytes
                ):
                    raise DocumentError(
                        "CHAT_IMPORT_TOO_LARGE",
                        "The shared conversation page exceeds the import size limit",
                        413,
                    )
                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > settings.chat_import_max_html_bytes:
                        raise DocumentError(
                            "CHAT_IMPORT_TOO_LARGE",
                            "The shared conversation page exceeds the import size limit",
                            413,
                        )
                    chunks.append(chunk)
                body = b"".join(chunks)
                if not body:
                    raise DocumentError(
                        "CHAT_IMPORT_EMPTY", "The shared conversation page is empty", 422
                    )
                return body.decode("utf-8", errors="replace"), current_url
    except DocumentError:
        raise
    except SourceError as exc:
        raise DocumentError(
            "CHAT_IMPORT_URL_INVALID",
            "The ChatGPT shared link did not resolve to a public network address",
            422,
        ) from exc
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        raise DocumentError(
            "CHAT_IMPORT_UNAVAILABLE",
            "The shared conversation could not be reached",
            503,
        ) from exc
    finally:
        if owned_client:
            client.close()


def _extract_loader(html: str) -> list[Any] | None:
    marker = "streamController.enqueue("
    decoder = json.JSONDecoder()
    for _attrs, script in _scripts(html):
        if marker not in script:
            continue
        cursor = 0
        while True:
            anchor = script.find(marker, cursor)
            if anchor < 0:
                break
            anchor += len(marker)
            quote = script.find('"', anchor)
            close = script.find(");", anchor)
            if quote >= 0 and (close < 0 or quote < close):
                try:
                    chunk, cursor = decoder.raw_decode(script, quote)
                except json.JSONDecodeError:
                    cursor = anchor + 1
                    continue
            else:
                if close < 0:
                    break
                chunk = script[anchor:close].strip()
                cursor = close + 2
            if isinstance(chunk, str) and chunk.lstrip().startswith("["):
                try:
                    payload = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, list):
                    return payload
    return None


def _decode_loader(loader: list[Any]) -> dict[str, Any]:
    cache: dict[int, Any] = {}

    def decode_key(key: Any) -> str:
        if isinstance(key, str) and key.startswith("_") and key[1:].isdigit():
            index = int(key[1:])
            if 0 <= index < len(loader) and isinstance(loader[index], str):
                return loader[index]
        return str(key)

    def resolve(value: Any) -> Any:
        if type(value) is int:
            if value < 0 or value >= len(loader):
                return value
            if value in cache:
                return cache[value]
            cache[value] = None
            cache[value] = resolve(loader[value])
            return cache[value]
        if isinstance(value, list):
            return [resolve(item) for item in value]
        if isinstance(value, dict):
            return {decode_key(key): resolve(item) for key, item in value.items()}
        return value

    decoded: dict[str, Any] = {}
    pairs = iter(loader[1:])
    for key in pairs:
        try:
            value = next(pairs)
        except StopIteration:
            break
        if isinstance(key, str) and key not in decoded:
            decoded[key] = resolve(value)
    return decoded


def _payload_data(html: str) -> Mapping[str, Any]:
    loader = _extract_loader(html)
    if loader is not None:
        decoded = _decode_loader(loader)
        loader_data = decoded.get("loaderData")
        if isinstance(loader_data, Mapping):
            route = loader_data.get("routes/share.$shareId.($action)")
            if isinstance(route, Mapping):
                server_response = route.get("serverResponse")
                if isinstance(server_response, Mapping):
                    data = server_response.get("data")
                    if isinstance(data, Mapping):
                        return data
    for attrs, script in _scripts(html):
        if attrs.get("id") != "__NEXT_DATA__":
            continue
        try:
            payload = json.loads(script)
        except json.JSONDecodeError as exc:
            raise DocumentError(
                "CHAT_IMPORT_PARSE_FAILED",
                "The shared conversation payload could not be decoded",
                422,
            ) from exc
        data = (
            payload.get("props", {})
            .get("pageProps", {})
            .get("serverResponse", {})
            .get("data", {})
        )
        if isinstance(data, Mapping):
            return data
    raise DocumentError(
        "CHAT_IMPORT_PARSE_FAILED",
        "The shared conversation format is not currently supported",
        422,
    )


def _clean_text(value: str) -> str:
    cleaned = PRIVATE_USE_PATTERN.sub("", value)
    return "\n".join(
        CITATION_TOKEN_PATTERN.sub("", line).rstrip() for line in cleaned.splitlines()
    ).strip()


def _allowed_public_image_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError:
        return None
    host = (parsed.hostname or "").casefold().rstrip(".")
    allowed_suffix = any(
        host == suffix or host.endswith(f".{suffix}")
        for suffix in ALLOWED_IMAGE_HOST_SUFFIXES
    )
    if (
        parsed.scheme != "https"
        or not host
        or port is not None
        or parsed.username
        or parsed.password
        or parsed.fragment
        or (not allowed_suffix and host not in ALLOWED_IMAGE_EXACT_HOSTS)
    ):
        return None
    return value


def _image_media(part: Mapping[str, Any]) -> ImportedChatMedia | None:
    value = part.get("asset_pointer") or part.get("url")
    pointer = _allowed_public_image_url(value)
    if pointer is None and not (
        isinstance(value, str) and SEDIMENT_IMAGE_PATTERN.fullmatch(value)
    ):
        return None
    alt_value = part.get("alt_text") or part.get("description")
    alt = _clean_text(alt_value)[:300] if isinstance(alt_value, str) else "ChatGPT image"
    return ImportedChatMedia(
        type="image", url=pointer or value, alt=alt or "ChatGPT image"
    )


def _content_and_media(
    message: Mapping[str, Any],
) -> tuple[str, tuple[ImportedChatMedia, ...]]:
    recipient = message.get("recipient")
    if isinstance(recipient, str) and recipient != "all":
        return "", ()
    content = message.get("content")
    if not isinstance(content, Mapping):
        return "", ()
    content_type = content.get("content_type")
    if content_type in SKIPPED_CONTENT_TYPES:
        return "", ()
    if content_type == "code":
        language = content.get("language")
        code = content.get("text")
        if not isinstance(code, str) or not code.strip():
            return "", ()
        label = language if isinstance(language, str) and language != "unknown" else ""
        return _clean_text(f"```{label}\n{code.rstrip()}\n```"), ()
    if content_type == "image_asset_pointer":
        media = _image_media(content)
        if media is not None:
            return "", (media,)
        return "[Image unavailable in imported ChatGPT snapshot]", ()

    parts = content.get("parts")
    if not isinstance(parts, list):
        return "", ()
    output: list[str] = []
    media_items: list[ImportedChatMedia] = []
    for part in parts:
        if isinstance(part, str):
            text = part
            stripped = text.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                try:
                    embedded = json.loads(stripped)
                except json.JSONDecodeError:
                    embedded = None
                if isinstance(embedded, Mapping):
                    candidate = embedded.get("response") or embedded.get("content")
                    if isinstance(candidate, str):
                        text = candidate
            if cleaned := _clean_text(text):
                output.append(cleaned)
            continue
        if not isinstance(part, Mapping):
            continue
        part_type = part.get("content_type") or part.get("type")
        if part_type == "text":
            text_value = part.get("text")
            texts = text_value if isinstance(text_value, list) else [text_value]
            for text in texts:
                if isinstance(text, str) and (cleaned := _clean_text(text)):
                    output.append(cleaned)
        elif part_type == "image_asset_pointer":
            media = _image_media(part)
            if media is not None:
                media_items.append(media)
            else:
                output.append("[Image unavailable in imported ChatGPT snapshot]")
        elif part_type == "file":
            output.append("[Attachment omitted from imported ChatGPT snapshot]")
    return "\n\n".join(output).strip(), tuple(media_items)


def _message_rows(data: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mapping = data.get("mapping")
    mapping_by_id = mapping if isinstance(mapping, Mapping) else {}
    sequence = data.get("linear_conversation")
    if not isinstance(sequence, list):
        return []
    rows: list[Mapping[str, Any]] = []
    for entry in sequence:
        if not isinstance(entry, Mapping):
            continue
        node: Any = entry
        node_id = entry.get("id")
        if isinstance(node_id, str) and isinstance(mapping_by_id.get(node_id), Mapping):
            node = mapping_by_id[node_id]
        message = node.get("message") if isinstance(node, Mapping) else None
        if isinstance(message, Mapping):
            rows.append(message)
    return rows


def parse_chatgpt_shared_snapshot(html: str, canonical_url: str) -> ChatGPTSharedSnapshot:
    data = _payload_data(html)
    title_value = data.get("title")
    title = _clean_text(title_value)[:300] if isinstance(title_value, str) else ""
    messages: list[ImportedChatMessage] = []
    total_characters = 0
    total_images = 0
    seen_media_urls: set[str] = set()
    for message in _message_rows(data):
        author = message.get("author")
        role = author.get("role") if isinstance(author, Mapping) else None
        content, media = _content_and_media(message)
        if role == "tool" and media:
            # ChatGPT image generation currently emits the visible image from a tool
            # message. Keep the public image as assistant output, but never import the
            # tool's private/raw text payload.
            role = "assistant"
            content = ""
        elif role not in {"user", "assistant"}:
            continue
        media = tuple(item for item in media if item.url not in seen_media_urls)
        seen_media_urls.update(item.url for item in media)
        if not content and not media:
            continue
        total_images += len(media)
        total_characters += len(content) + sum(
            len(item.url) + len(item.alt) for item in media
        )
        if len(messages) >= settings.chat_import_max_messages:
            raise DocumentError(
                "CHAT_IMPORT_TOO_LARGE",
                "The shared conversation contains too many visible messages",
                413,
            )
        if total_characters > settings.chat_import_max_total_chars:
            raise DocumentError(
                "CHAT_IMPORT_TOO_LARGE",
                "The shared conversation text exceeds the import size limit",
                413,
            )
        if total_images > settings.chat_import_max_images:
            raise DocumentError(
                "CHAT_IMPORT_TOO_LARGE",
                "The shared conversation contains too many public images",
                413,
            )
        created_at = None
        created_value = message.get("create_time")
        if isinstance(created_value, (int, float)):
            try:
                created_at = datetime.fromtimestamp(float(created_value), tz=UTC)
            except (OSError, OverflowError, ValueError):
                created_at = None
        messages.append(
            ImportedChatMessage(
                role=role,
                content=content,
                created_at=created_at,
                media=media,
            )
        )
    if not messages:
        raise DocumentError(
            "CHAT_IMPORT_EMPTY",
            "No visible user or assistant messages were found in the shared conversation",
            422,
        )
    canonical_snapshot = json.dumps(
        {
            "title": title,
            "messages": [
                {
                    "role": item.role,
                    "content": item.content,
                    "media": [
                        {"type": media.type, "url": media.url, "alt": media.alt}
                        for media in item.media
                    ],
                }
                for item in messages
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return ChatGPTSharedSnapshot(
        title=title or "Cuộc trò chuyện nhập từ ChatGPT",
        messages=tuple(messages),
        canonical_url=canonical_url,
        snapshot_hash=hashlib.sha256(canonical_snapshot).hexdigest(),
        total_characters=total_characters,
    )


def _share_id(canonical_url: str) -> str:
    return canonical_url.rstrip("/").rsplit("/", 1)[-1]


def _download_url_for_media(
    client: httpx.Client, media_url: str, canonical_url: str
) -> str:
    sediment = SEDIMENT_IMAGE_PATTERN.fullmatch(media_url)
    if sediment is None:
        return media_url
    endpoint = (
        "https://chatgpt.com/backend-anon/files/download/"
        f"{sediment.group('file_id')}"
    )
    try:
        validate_public_url(endpoint)
        with client.stream(
            "GET",
            endpoint,
            params={
                "shared_conversation_id": _share_id(canonical_url),
                "inline": "false",
                "download_intent": "false",
            },
            headers={
                "User-Agent": settings.intake_user_agent or DEFAULT_USER_AGENT,
                "Accept": "application/json",
                "Referer": canonical_url,
            },
        ) as response:
            assert_peer_is_public(response)
            response.raise_for_status()
            declared = response.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > 64 * 1024:
                raise ValueError("asset descriptor is too large")
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > 64 * 1024:
                    raise ValueError("asset descriptor is too large")
                chunks.append(chunk)
        payload = json.loads(b"".join(chunks))
        download_url = payload.get("download_url") if isinstance(payload, Mapping) else None
        if _allowed_public_image_url(download_url) is None:
            raise ValueError("asset descriptor returned an untrusted URL")
        return download_url
    except (
        SourceError,
        httpx.HTTPError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        ValueError,
    ) as exc:
        raise DocumentError(
            "CHAT_IMPORT_IMAGE_UNAVAILABLE",
            "A public ChatGPT image could not be resolved",
            502,
        ) from exc


def _download_image(client: httpx.Client, url: str) -> tuple[bytes, str]:
    current_url = url
    redirects = 0
    headers = {
        "User-Agent": settings.intake_user_agent or DEFAULT_USER_AGENT,
        "Accept": "image/avif,image/webp,image/png,image/jpeg,image/gif;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    }
    try:
        while True:
            if _allowed_public_image_url(current_url) is None:
                raise ValueError("image URL is not allowlisted")
            validate_public_url(current_url)
            with client.stream("GET", current_url, headers=headers) as response:
                assert_peer_is_public(response)
                if response.status_code in REDIRECT_STATUSES:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("image redirect is missing a location")
                    redirects += 1
                    if redirects > settings.chat_import_max_redirects:
                        raise ValueError("image redirected too many times")
                    current_url = urljoin(current_url, location)
                    continue
                response.raise_for_status()
                mime_type = normalize_content_type(response.headers.get("content-type"))
                if mime_type not in ALLOWED_IMAGE_TYPES:
                    raise ValueError("asset is not a supported raster image")
                declared = response.headers.get("content-length")
                if (
                    declared
                    and declared.isdigit()
                    and int(declared) > settings.chat_import_max_image_bytes
                ):
                    raise DocumentError(
                        "CHAT_IMPORT_IMAGE_TOO_LARGE",
                        "A public ChatGPT image exceeds the import size limit",
                        413,
                    )
                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > settings.chat_import_max_image_bytes:
                        raise DocumentError(
                            "CHAT_IMPORT_IMAGE_TOO_LARGE",
                            "A public ChatGPT image exceeds the import size limit",
                            413,
                        )
                    chunks.append(chunk)
                image = b"".join(chunks)
                if not image:
                    raise ValueError("image response is empty")
                return image, mime_type
    except DocumentError:
        raise
    except (SourceError, httpx.HTTPError, ValueError) as exc:
        raise DocumentError(
            "CHAT_IMPORT_IMAGE_UNAVAILABLE",
            "A public ChatGPT image could not be downloaded",
            502,
        ) from exc


async def _bytes_stream(value: bytes):
    for offset in range(0, len(value), 64 * 1024):
        yield value[offset : offset + 64 * 1024]


async def _materialize_snapshot_media(
    snapshot: ChatGPTSharedSnapshot,
    client: httpx.Client,
    storage: ObjectStorage,
) -> ChatGPTSharedSnapshot:
    cached: dict[str, ImportedChatMedia | None] = {}
    stored_keys: list[str] = []
    messages: list[ImportedChatMessage] = []
    total_image_bytes = 0
    try:
        for message in snapshot.messages:
            resolved_media: list[ImportedChatMedia] = []
            unavailable = 0
            for media in message.media:
                if media.url in cached:
                    resolved = cached[media.url]
                    if resolved is None:
                        unavailable += 1
                    else:
                        resolved_media.append(replace(resolved, alt=media.alt))
                    continue
                last_error: DocumentError | None = None
                for attempt in range(settings.chat_import_image_retries + 1):
                    try:
                        download_url = _download_url_for_media(
                            client, media.url, snapshot.canonical_url
                        )
                        content, mime_type = _download_image(client, download_url)
                        last_error = None
                        break
                    except DocumentError as exc:
                        if exc.code != "CHAT_IMPORT_IMAGE_UNAVAILABLE":
                            raise
                        last_error = exc
                        if attempt < settings.chat_import_image_retries:
                            time.sleep(
                                settings.chat_import_image_retry_backoff_seconds
                                * (2**attempt)
                            )
                if last_error is not None:
                    cached[media.url] = None
                    unavailable += 1
                    continue
                total_image_bytes += len(content)
                if total_image_bytes > settings.chat_import_max_total_image_bytes:
                    raise DocumentError(
                        "CHAT_IMPORT_IMAGES_TOO_LARGE",
                        "The shared conversation images exceed the total import size limit",
                        413,
                    )
                source_hash = hashlib.sha256(media.url.encode("utf-8")).hexdigest()[:20]
                extension = ALLOWED_IMAGE_TYPES[mime_type]
                object_key = (
                    f"chat-imports/{_share_id(snapshot.canonical_url)}/"
                    f"{source_hash}-{uuid.uuid4().hex}.{extension}"
                )
                stored = await storage.put(
                    object_key,
                    _bytes_stream(content),
                    {"mime_type": mime_type, "source": "chatgpt_shared"},
                )
                stored_keys.append(stored.key)
                resolved = ImportedChatMedia(
                    type="image",
                    url="",
                    alt=media.alt,
                    storage_key=stored.key,
                    mime_type=mime_type,
                    size_bytes=stored.size_bytes,
                    sha256=stored.sha256,
                )
                cached[media.url] = resolved
                resolved_media.append(resolved)
            content = message.content
            if unavailable:
                notices = "\n\n".join(
                    "[Image unavailable in imported ChatGPT snapshot]"
                    for _ in range(unavailable)
                )
                content = f"{content}\n\n{notices}".strip()
            messages.append(replace(message, content=content, media=tuple(resolved_media)))
        return replace(
            snapshot,
            messages=tuple(messages),
            stored_object_keys=tuple(stored_keys),
        )
    except Exception:
        for key in stored_keys:
            try:
                await storage.delete(key)
            except DocumentError:
                pass
        raise


def import_chatgpt_shared_snapshot(
    url: str, storage: ObjectStorage | None = None
) -> ChatGPTSharedSnapshot:
    canonical_url = validate_chatgpt_share_url(url)
    with httpx.Client(
        follow_redirects=False,
        timeout=httpx.Timeout(settings.chat_import_timeout_seconds),
    ) as client:
        html, final_url = _fetch_share_html(canonical_url, client)
        snapshot = parse_chatgpt_shared_snapshot(html, final_url)
        if storage is None or not any(message.media for message in snapshot.messages):
            return snapshot
        return asyncio.run(_materialize_snapshot_media(snapshot, client, storage))
