import json

import httpx
import pytest

from app.core.config import settings
from app.main import app
from app.models import AuditEvent, ChatMessage, ChatSession
from app.services.chatgpt_import import (
    ChatGPTSharedSnapshot,
    ImportedChatMedia,
    ImportedChatMessage,
    import_chatgpt_shared_snapshot,
    parse_chatgpt_shared_snapshot,
    validate_chatgpt_share_url,
)
from app.services.documents import get_object_storage
from app.services.object_storage import DocumentError, LocalObjectStorage
from app.services.providers.openai_graph_chat import GraphProviderResponse

SHARE_URL = "https://chatgpt.com/share/12345678-1234-1234-1234-123456789abc"


class RecordingProvider:
    name = "deepseek"
    model = "deepseek-test"

    def __init__(self) -> None:
        self.requests: list[dict] = []

    def respond(self, **kwargs):
        self.requests.append(kwargs)
        return GraphProviderResponse(
            response_id="response-local",
            request_id="request-local",
            text="Continued locally.",
            usage={"input_tokens": 12, "output_tokens": 3, "total_tokens": 15},
        )


def legacy_share_html() -> str:
    def message(role: str, content: dict, **extra):
        return {
            "author": {"role": role},
            "content": content,
            **extra,
        }

    data = {
        "title": "Imported planning chat",
        "mapping": {
            "system": {
                "message": message(
                    "system", {"content_type": "text", "parts": ["hidden"]}
                )
            },
            "user": {
                "message": message(
                    "user",
                    {
                        "content_type": "multimodal_text",
                        "parts": [
                            "Plan a governed agent.",
                            {
                                "content_type": "image_asset_pointer",
                                "asset_pointer": "https://files.oaiusercontent.com/public/diagram.png?sig=test",
                                "alt_text": "Governed agent diagram",
                            },
                        ],
                    },
                    create_time=1_700_000_000,
                )
            },
            "thought": {
                "message": message(
                    "assistant", {"content_type": "thoughts", "parts": ["secret"]}
                )
            },
            "assistant": {
                "message": message(
                    "assistant",
                    {
                        "content_type": "text",
                        "parts": ["Use a human review gate."],
                    },
                )
            },
        },
        "linear_conversation": [
            {"id": "system"},
            {"id": "user"},
            {"id": "thought"},
            {"id": "assistant"},
        ],
    }
    payload = {"props": {"pageProps": {"serverResponse": {"data": data}}}}
    return f'<html><script id="__NEXT_DATA__">{json.dumps(payload)}</script></html>'


@pytest.mark.parametrize(
    "url",
    [
        "http://chatgpt.com/share/12345678-1234-1234-1234-123456789abc",
        "https://chatgpt.com.evil.test/share/12345678-1234-1234-1234-123456789abc",
        "https://chatgpt.com:443/share/12345678-1234-1234-1234-123456789abc",
        "https://chatgpt.com/share/12345678-1234-1234-1234-123456789abc?x=1",
        "https://chatgpt.com/backend-api/share/12345678-1234-1234-1234-123456789abc",
    ],
)
def test_chatgpt_share_url_is_exact_and_cookie_free(url):
    with pytest.raises(DocumentError) as error:
        validate_chatgpt_share_url(url)

    assert error.value.code == "CHAT_IMPORT_URL_INVALID"


def test_legacy_shared_snapshot_extracts_only_visible_conversation_content():
    snapshot = parse_chatgpt_shared_snapshot(legacy_share_html(), SHARE_URL)

    assert snapshot.title == "Imported planning chat"
    assert [message.role for message in snapshot.messages] == ["user", "assistant"]
    assert snapshot.messages[0].content == "Plan a governed agent."
    assert snapshot.messages[0].media == (
        ImportedChatMedia(
            type="image",
            url="https://files.oaiusercontent.com/public/diagram.png?sig=test",
            alt="Governed agent diagram",
        ),
    )
    assert snapshot.messages[1].content == "Use a human review gate."
    assert "hidden" not in " ".join(message.content for message in snapshot.messages)
    assert "secret" not in " ".join(message.content for message in snapshot.messages)
    assert len(snapshot.snapshot_hash) == 64


def test_current_react_loader_shared_snapshot_is_supported():
    data = {
        "title": "Current shared format",
        "mapping": {
            "one": {
                "message": {
                    "author": {"role": "user"},
                    "content": {"content_type": "text", "parts": ["Current payload"]},
                }
            }
        },
        "linear_conversation": [{"id": "one"}],
    }
    loader = [
        {},
        "loaderData",
        {
            "routes/share.$shareId.($action)": {
                "serverResponse": {"data": data}
            }
        },
    ]
    encoded_loader = json.dumps(json.dumps(loader))
    html = (
        "<html><script>window.__reactRouterContext.streamController.enqueue("
        f"{encoded_loader});</script></html>"
    )

    snapshot = parse_chatgpt_shared_snapshot(html, SHARE_URL)

    assert snapshot.title == "Current shared format"
    assert [(message.role, message.content) for message in snapshot.messages] == [
        ("user", "Current payload")
    ]


def test_generated_image_tool_output_is_imported_as_assistant_media_only():
    html = legacy_share_html().replace(
        '"role": "user"', '"role": "tool"', 1
    )

    snapshot = parse_chatgpt_shared_snapshot(html, SHARE_URL)

    assert [message.role for message in snapshot.messages] == ["assistant", "assistant"]
    assert snapshot.messages[0].content == ""
    assert len(snapshot.messages[0].media) == 1
    assert snapshot.messages[0].media[0].alt == "Governed agent diagram"


def mock_chatgpt_transport(monkeypatch, handler) -> None:
    real_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        "app.services.chatgpt_import.validate_public_url", lambda _url: None
    )
    monkeypatch.setattr(
        "app.services.chatgpt_import.httpx.Client",
        lambda **kwargs: real_client(
            transport=transport,
            follow_redirects=kwargs.get("follow_redirects", False),
            timeout=kwargs.get("timeout"),
        ),
    )


def test_fetch_rejects_cross_host_redirect(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"location": "https://example.com/share/not-allowed"},
            request=request,
        )

    mock_chatgpt_transport(monkeypatch, handler)

    with pytest.raises(DocumentError) as error:
        import_chatgpt_shared_snapshot(SHARE_URL)

    assert error.value.code == "CHAT_IMPORT_URL_INVALID"


def test_fetch_rejects_declared_oversized_snapshot(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "content-type": "text/html",
                "content-length": str(settings.chat_import_max_html_bytes + 1),
            },
            content=b"ignored",
            request=request,
        )

    mock_chatgpt_transport(monkeypatch, handler)

    with pytest.raises(DocumentError) as error:
        import_chatgpt_shared_snapshot(SHARE_URL)

    assert error.value.code == "CHAT_IMPORT_TOO_LARGE"


def test_current_sediment_image_is_resolved_and_cached_locally(monkeypatch, tmp_path):
    sediment_pointer = (
        "sediment://file_00000000ed5c71fd80aa38433218a5c7"
        "?shared_conversation_id=12345678-1234-1234-1234-123456789abc"
    )
    share_html = legacy_share_html().replace(
        "https://files.oaiusercontent.com/public/diagram.png?sig=test",
        sediment_pointer,
    )
    image_bytes = b"public-chatgpt-image"
    descriptor_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal descriptor_calls
        if request.url.path.startswith("/share/"):
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                content=share_html.encode(),
                request=request,
            )
        if request.url.path.startswith("/backend-anon/files/download/"):
            assert request.url.params["shared_conversation_id"] == SHARE_URL.rsplit("/", 1)[-1]
            descriptor_calls += 1
            if descriptor_calls == 1:
                return httpx.Response(503, request=request)
            return httpx.Response(
                200,
                json={
                    "download_url": (
                        "https://files.oaiusercontent.com/public/generated.webp?sig=test"
                    )
                },
                request=request,
            )
        return httpx.Response(
            200,
            headers={"content-type": "image/webp"},
            content=image_bytes,
            request=request,
        )

    mock_chatgpt_transport(monkeypatch, handler)
    monkeypatch.setattr(settings, "chat_import_image_retry_backoff_seconds", 0)
    storage = LocalObjectStorage(tmp_path, settings.chat_import_max_image_bytes)

    snapshot = import_chatgpt_shared_snapshot(SHARE_URL, storage)

    media = snapshot.messages[0].media[0]
    assert media.url == ""
    assert media.storage_key is not None
    assert media.mime_type == "image/webp"
    assert media.size_bytes == len(image_bytes)
    assert snapshot.stored_object_keys == (media.storage_key,)
    assert (tmp_path / media.storage_key).read_bytes() == image_bytes
    assert descriptor_calls == 2


def test_message_limit_fails_instead_of_silently_truncating(monkeypatch):
    monkeypatch.setattr(settings, "chat_import_max_messages", 1)

    with pytest.raises(DocumentError) as error:
        parse_chatgpt_shared_snapshot(legacy_share_html(), SHARE_URL)

    assert error.value.code == "CHAT_IMPORT_TOO_LARGE"


def test_untrusted_or_non_https_image_pointer_is_not_exposed():
    html = legacy_share_html().replace(
        "https://files.oaiusercontent.com/public/diagram.png?sig=test",
        "http://127.0.0.1/internal.png",
    )

    snapshot = parse_chatgpt_shared_snapshot(html, SHARE_URL)

    assert snapshot.messages[0].media == ()
    assert "[Image unavailable in imported ChatGPT snapshot]" in snapshot.messages[0].content


def test_public_image_limit_fails_instead_of_silently_dropping_media(monkeypatch):
    monkeypatch.setattr(settings, "chat_import_max_images", 0)

    with pytest.raises(DocumentError) as error:
        parse_chatgpt_shared_snapshot(legacy_share_html(), SHARE_URL)

    assert error.value.code == "CHAT_IMPORT_TOO_LARGE"


def test_import_persists_provenance_and_continues_only_in_local_session(
    client, db, monkeypatch
):
    provider = RecordingProvider()
    snapshot = ChatGPTSharedSnapshot(
        title="Imported planning chat",
        messages=(
            ImportedChatMessage(
                role="user",
                content="Plan a governed agent.",
                media=(
                    ImportedChatMedia(
                        type="image",
                        url="https://files.oaiusercontent.com/public/diagram.png?sig=test",
                        alt="Governed agent diagram",
                    ),
                ),
            ),
            ImportedChatMessage(role="assistant", content="Use a human review gate."),
        ),
        canonical_url=SHARE_URL,
        snapshot_hash="a" * 64,
        total_characters=49,
    )
    monkeypatch.setattr(
        "app.services.graph_chat.import_chatgpt_shared_snapshot",
        lambda _url, _storage: snapshot,
    )
    monkeypatch.setattr(
        "app.services.graph_chat.graph_chat_provider", lambda _name: provider
    )

    imported = client.post(
        "/api/v1/chat/imports/chatgpt",
        json={"url": SHARE_URL, "provider": "deepseek"},
    )

    assert imported.status_code == 201, imported.text
    session_id = imported.json()["id"]
    assert imported.json()["source_type"] == "chatgpt_shared"
    assert imported.json()["source_url"] == SHARE_URL
    assert imported.json()["source_snapshot_hash"] == "a" * 64
    assert imported.json()["imported_message_count"] == 2
    stored = db.get(ChatSession, session_id)
    assert stored is not None
    messages = (
        db.query(ChatMessage)
        .filter_by(session_id=session_id)
        .order_by(ChatMessage.created_at, ChatMessage.id)
        .all()
    )
    assert [message.origin_type for message in messages] == [
        "chatgpt_shared",
        "chatgpt_shared",
    ]
    assert messages[0].media_json == [
        {
            "type": "image",
            "url": "https://files.oaiusercontent.com/public/diagram.png?sig=test",
            "alt": "Governed agent diagram",
        }
    ]
    listed_messages = client.get(f"/api/v1/chat/sessions/{session_id}/messages")
    assert listed_messages.status_code == 200
    assert listed_messages.json()[0]["media"] == messages[0].media_json
    audit = db.query(AuditEvent).filter_by(action="chat.import.completed").one()
    serialized_audit = json.dumps(audit.payload)
    assert SHARE_URL not in serialized_audit
    assert "Plan a governed agent" not in serialized_audit
    assert audit.payload["snapshot_hash"] == "a" * 64

    continued = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "Continue with implementation steps."},
    )

    assert continued.status_code == 200, continued.text
    assert continued.json()["assistant_message"]["content"] == "Continued locally."
    assert continued.json()["user_message"]["origin_type"] == "local"
    assert continued.json()["assistant_message"]["origin_type"] == "local"
    sent_history = provider.requests[0]["input_items"]
    assert [item["content"] for item in sent_history] == [
        "Plan a governed agent.",
        "Use a human review gate.",
        "Continue with implementation steps.",
    ]
    assert "oaiusercontent.com" not in json.dumps(sent_history)


def test_cached_chat_image_is_served_from_bounded_local_endpoint(client, db):
    class MemoryStorage:
        async def open(self, key):
            assert key == "chat-imports/share/image.webp"
            yield b"cached-image"

    session = ChatSession(title="Cached image", model_name="local-test")
    db.add(session)
    db.flush()
    message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content="",
        origin_type="chatgpt_shared",
        media_json=[
            {
                "type": "image",
                "alt": "Cached generated image",
                "storage_key": "chat-imports/share/image.webp",
                "mime_type": "image/webp",
                "size_bytes": 12,
                "sha256": "a" * 64,
            }
        ],
    )
    db.add(message)
    db.commit()
    app.dependency_overrides[get_object_storage] = lambda: MemoryStorage()

    listed = client.get(f"/api/v1/chat/sessions/{session.id}/messages")
    media_url = listed.json()[0]["media"][0]["url"]
    response = client.get(media_url)

    assert media_url == f"/api/v1/chat/messages/{message.id}/media/0"
    assert response.status_code == 200
    assert response.content == b"cached-image"
    assert response.headers["content-type"] == "image/webp"
    assert response.headers["cache-control"] == "private, max-age=31536000, immutable"
