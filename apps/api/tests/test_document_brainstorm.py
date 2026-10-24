from app.models import ChatMessage, ChatSession, DocumentGraphWorkspace, DocumentSourceVersion
from app.schemas.documents import DocumentBrainstormRequest
from app.services.document_brainstorm import brainstorm_document, select_document_context
from app.services.providers.openai_graph_chat import GraphProviderResponse


class BrainstormProviderDouble:
    name = "deepseek"
    model = "brainstorm-test"

    def __init__(self):
        self.requests = []

    def respond(self, **kwargs):
        self.requests.append(kwargs)
        return GraphProviderResponse(
            text="Thử chia kiến trúc thành perception, planning và control.",
            usage={"input_tokens": 20, "output_tokens": 10, "total_tokens": 30},
        )


def test_context_prefers_selected_range_and_stays_bounded():
    source = "A" * 8_000 + "SELECTED ROBOT CONTROL" + "B" * 8_000
    start = source.index("SELECTED")
    context, truncated = select_document_context(
        source,
        "How should control work?",
        selection_start=start,
        selection_end=start + len("SELECTED ROBOT CONTROL"),
        limit=2_000,
    )

    assert truncated is True
    assert "SELECTED ROBOT CONTROL" in context
    assert len(context) <= 2_000


def test_document_brainstorm_is_redacted_bounded_and_non_mutating(db):
    runtime = BrainstormProviderDouble()
    request = DocumentBrainstormRequest(
        source=("Robot control evidence. " * 1_000) + "owner@example.com",
        message="Hãy brainstorm cấu trúc nghiên cứu.",
        history=[{"role": "assistant", "content": "Ta đang bàn về robot."}],
        provider="deepseek",
    )
    before = (
        db.query(ChatSession).count(),
        db.query(ChatMessage).count(),
        db.query(DocumentGraphWorkspace).count(),
        db.query(DocumentSourceVersion).count(),
    )

    result = brainstorm_document(request, runtime=runtime)

    assert result.content.startswith("Thử chia kiến trúc")
    assert result.source_context_truncated is True
    sent = runtime.requests[0]
    assert sent["tools"] == []
    assert "owner@example.com" not in sent["instructions"]
    assert len(sent["instructions"]) < 14_000
    assert before == (
        db.query(ChatSession).count(),
        db.query(ChatMessage).count(),
        db.query(DocumentGraphWorkspace).count(),
        db.query(DocumentSourceVersion).count(),
    )


def test_document_brainstorm_endpoint_returns_provider_provenance(client, monkeypatch):
    runtime = BrainstormProviderDouble()
    monkeypatch.setattr(
        "app.services.document_brainstorm.graph_chat_provider", lambda _name: runtime
    )

    response = client.post(
        "/api/v1/documents/brainstorm",
        json={
            "source": "Robot nhận diện và gắp cà rốt.",
            "message": "Có thể thử nghiệm những biến nào?",
            "provider": "deepseek",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "content": "Thử chia kiến trúc thành perception, planning và control.",
        "provider_name": "deepseek",
        "model_name": "brainstorm-test",
        "source_context_truncated": False,
    }


def test_document_brainstorm_rejects_invalid_selection_and_oversized_history(client):
    invalid_selection = client.post(
        "/api/v1/documents/brainstorm",
        json={"source": "short", "message": "Question", "selection_start": 1},
    )
    oversized_history = client.post(
        "/api/v1/documents/brainstorm",
        json={
            "source": "source",
            "message": "Question",
            "history": [
                {"role": "user", "content": "a" * 4_000},
                {"role": "assistant", "content": "b" * 4_000},
                {"role": "user", "content": "c" * 4_000},
                {"role": "assistant", "content": "d" * 4_000},
                {"role": "user", "content": "e" * 4_000},
                {"role": "assistant", "content": "f"},
            ],
        },
    )

    assert invalid_selection.status_code == 422
    assert oversized_history.status_code == 422
