from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.models import (
    Attachment,
    ChatMessage,
    ChatSession,
    DocumentGraphNode,
    DocumentGraphWorkspace,
    GraphChangeSet,
    GraphMutation,
    KnowledgeNode,
    NodeEvidence,
    ResearchItem,
)
from app.services.graph_chat import (
    ReversibleCloudRedactor,
    build_scope_context,
    graph_chat_tools,
    redact_cloud_text,
)
from app.services.object_storage import DocumentError
from app.services.providers.openai_graph_chat import (
    DeepSeekGraphChatProvider,
    GraphProviderResponse,
    GraphToolCall,
    OpenAIGraphChatProvider,
    graph_chat_provider,
)


class SequencedProvider:
    name = "openai"
    model = "test-graph-chat"

    def __init__(self, responses: list[GraphProviderResponse]):
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    def respond(self, **kwargs) -> GraphProviderResponse:
        self.requests.append(kwargs)
        return self.responses.pop(0)


def tool_response(name: str, arguments: dict[str, Any], call_id: str = "call-1"):
    return GraphProviderResponse(
        response_id="response-tools",
        request_id="request-tools",
        tool_calls=[GraphToolCall(call_id=call_id, name=name, arguments=arguments)],
        output_items=[
            {
                "type": "function_call",
                "call_id": call_id,
                "name": name,
                "arguments": "{}",
            }
        ],
        usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    )


def final_response(text: str = "Here is a governed proposal."):
    return GraphProviderResponse(
        response_id="response-final",
        request_id="request-final",
        text=text,
        usage={"input_tokens": 8, "output_tokens": 7, "total_tokens": 15},
    )


def patch_runtime(monkeypatch, runtime: SequencedProvider) -> None:
    monkeypatch.setattr("app.services.graph_chat.graph_chat_provider", lambda _name: runtime)


def create_document_evidence(db):
    research = ResearchItem(
        title="Grounded memory",
        type="reference",
        status="draft",
        collection_method="upload",
        content="Episodic memory improves continuity.",
        authors=[],
        metadata_json={},
    )
    db.add(research)
    db.flush()
    attachment = Attachment(
        research_id=research.id,
        filename="memory.md",
        object_key=f"tests/{research.id}.md",
        mime_type="text/markdown",
        size_bytes=40,
    )
    db.add(attachment)
    db.flush()
    workspace = DocumentGraphWorkspace(
        research_id=research.id,
        attachment_id=attachment.id,
        storage_object_key=attachment.object_key,
        content_hash="f" * 64,
        processing_status="needs_review",
        review_status="needs_review",
        extraction_limitations=[],
    )
    db.add(workspace)
    db.flush()
    node = DocumentGraphNode(
        workspace_id=workspace.id,
        local_key="episodic-memory",
        node_type="concept",
        label="Episodic Memory",
        summary="Agent memory for prior events",
        confidence=0.9,
        evidence_status="supported",
        metadata_json={},
    )
    db.add(node)
    db.flush()
    evidence = NodeEvidence(
        owner_kind="document_node",
        owner_id=node.id,
        source_document_id=research.id,
        location={"section": "Findings"},
        excerpt="Episodic memory improves continuity.",
        content_hash=workspace.content_hash,
        extraction_method="test",
        provenance={"workspace_id": workspace.id},
    )
    db.add(evidence)
    db.commit()
    return workspace, evidence


def test_chat_session_crud_and_close(client, db, monkeypatch):
    runtime = SequencedProvider([final_response("Brainstorm response")])
    patch_runtime(monkeypatch, runtime)

    created = client.post(
        "/api/v1/chat/sessions",
        json={"title": "Architecture ideas", "scope_type": "graph", "provider": "openai"},
    )
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]
    turn = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "How should evaluator agents fit?"},
    )
    messages = client.get(f"/api/v1/chat/sessions/{session_id}/messages")
    closed = client.post(f"/api/v1/chat/sessions/{session_id}/close")
    after_close = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages", json={"content": "Continue"}
    )

    assert turn.status_code == 200, turn.text
    assert turn.json()["assistant_message"]["content"] == "Brainstorm response"
    assert len(messages.json()) == 2
    assert closed.json()["status"] == "closed"
    assert after_close.status_code == 409
    assert db.query(ChatSession).count() == 1


def test_chat_proposal_stays_in_change_set_until_grounded_and_approved(client, db, monkeypatch):
    runtime = SequencedProvider(
        [
            tool_response(
                "propose_node",
                {
                    "canonical_label": "Adaptive Evaluator Agent",
                    "node_type": "AgentPattern",
                    "description": "An evaluator that adjusts its rubric.",
                    "primary_parent_id": None,
                    "confidence": 0.72,
                    "evidence_ids": [],
                    "reasoning_summary": "Potential governance pattern.",
                },
            ),
            final_response(),
        ]
    )
    patch_runtime(monkeypatch, runtime)
    session = client.post(
        "/api/v1/chat/sessions", json={"scope_type": "graph", "provider": "openai"}
    ).json()
    before_nodes = db.query(KnowledgeNode).count()

    turn = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages",
        json={"content": "Add an adaptive evaluator agent to the graph."},
    )

    assert turn.status_code == 200, turn.text
    change_set_id = turn.json()["change_set_id"]
    change_set = db.get(GraphChangeSet, change_set_id)
    mutation = db.query(GraphMutation).filter_by(change_set_id=change_set_id).one()
    assert change_set.origin_type == "chat"
    assert change_set.lifecycle_status == "draft"
    assert mutation.proposed_json["evidence_status"] == "evidence_pending"
    assert mutation.validation_status == "error"
    assert client.post(f"/api/v1/graph/change-sets/{change_set_id}/apply").status_code == 409
    assert db.query(KnowledgeNode).count() == before_nodes


def test_document_scoped_chat_can_create_a_grounded_reviewable_proposal(client, db, monkeypatch):
    workspace, evidence = create_document_evidence(db)
    research = db.get(ResearchItem, workspace.research_id)
    research.content += " Contact document-owner@example.com for the review record."
    db.commit()
    runtime = SequencedProvider(
        [
            tool_response("get_document_evidence", {"query": "episodic", "limit": 5}, "call-read"),
            tool_response(
                "propose_node",
                {
                    "canonical_label": "Episodic Memory",
                    "node_type": "Concept",
                    "description": "Memory of prior agent events.",
                    "primary_parent_id": None,
                    "confidence": 0.9,
                    "evidence_ids": [evidence.id],
                    "reasoning_summary": "Grounded in the uploaded document.",
                },
                "call-propose",
            ),
            final_response("I linked the idea to source evidence for review."),
        ]
    )
    patch_runtime(monkeypatch, runtime)
    session = client.post(
        "/api/v1/chat/sessions",
        json={
            "scope_type": "document",
            "scope_id": workspace.id,
            "provider": "openai",
        },
    ).json()

    turn = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages",
        json={"content": "Capture the episodic memory finding."},
    )
    change_set_id = turn.json()["change_set_id"]
    mutation = db.query(GraphMutation).filter_by(change_set_id=change_set_id).one()

    assert turn.status_code == 200, turn.text
    instructions = runtime.requests[0]["instructions"]
    assert "Episodic memory improves continuity." in instructions
    assert "document_text" in instructions
    assert "document-owner@example.com" not in instructions
    assert "[REDACTED_EMAIL]" in instructions
    assert mutation.validation_status in {"valid", "warning"}
    assert mutation.proposed_json["evidence_preview"][0]["id"] == evidence.id
    assert client.post(f"/api/v1/graph/change-sets/{change_set_id}/approve").status_code == 200
    assert db.query(KnowledgeNode).filter_by(canonical_label="Episodic Memory").count() == 0
    assert client.post(f"/api/v1/graph/change-sets/{change_set_id}/apply").status_code == 200
    assert db.query(KnowledgeNode).filter_by(canonical_label="Episodic Memory").count() == 1


def test_document_scope_context_bounds_canonical_text(db):
    workspace, _ = create_document_evidence(db)
    research = db.get(ResearchItem, workspace.research_id)
    research.content = "bounded evidence " * settings.chat_max_context_chars
    db.commit()
    session = ChatSession(
        scope_type="document",
        scope_id=workspace.id,
        provider_name="openai",
        model_name="test-model",
    )

    context = build_scope_context(db, session)

    assert context["document_text_truncated"] is True
    assert len(context["document_text"]) <= settings.chat_max_context_chars // 2
    assert context["document_text"].startswith("bounded evidence")


def test_unavailable_publish_tool_is_recorded_but_cannot_write_graph(client, db, monkeypatch):
    runtime = SequencedProvider(
        [tool_response("publish_change_set", {"id": "unsafe"}), final_response("Not allowed.")]
    )
    patch_runtime(monkeypatch, runtime)
    session = client.post(
        "/api/v1/chat/sessions", json={"scope_type": "graph", "provider": "openai"}
    ).json()
    before = db.query(KnowledgeNode).count()

    turn = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages",
        json={"content": "Publish directly."},
    )

    assert turn.status_code == 200
    assert turn.json()["change_set_id"] is None
    assert db.query(KnowledgeNode).count() == before
    assistant = db.query(ChatMessage).filter_by(role="assistant").one()
    assert assistant.tool_results_json[0]["result"]["error"]["code"] == "CHAT_TOOL_NOT_ALLOWED"


def test_tool_loop_limit_is_typed_persisted_and_cannot_write_graph(client, db, monkeypatch):
    arguments = {
        "canonical_label": "Looping Agent",
        "node_type": "AgentPattern",
        "description": "A proposal that must never escape a failed turn.",
        "primary_parent_id": None,
        "confidence": 0.5,
        "evidence_ids": [],
        "reasoning_summary": "Test bounded orchestration.",
    }
    runtime = SequencedProvider(
        [
            tool_response("propose_node", arguments, "call-first"),
            tool_response("propose_node", arguments, "call-over-limit"),
        ]
    )
    patch_runtime(monkeypatch, runtime)
    monkeypatch.setattr(settings, "chat_max_tool_loops", 1)
    session = client.post(
        "/api/v1/chat/sessions", json={"scope_type": "graph", "provider": "openai"}
    ).json()
    before = db.query(KnowledgeNode).count()

    turn = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages",
        json={"content": "Keep proposing forever."},
    )

    assert turn.status_code == 409
    assert turn.json()["error"]["code"] == "CHAT_TOOL_LOOP_LIMIT"
    assert db.query(KnowledgeNode).count() == before
    assert db.query(GraphChangeSet).filter_by(origin_type="chat").count() == 0
    failure = db.query(ChatMessage).filter_by(role="assistant").one()
    assert failure.error_code == "CHAT_TOOL_LOOP_LIMIT"
    assert len(failure.tool_calls_json) == 1


def test_openai_adapter_uses_strict_tools_store_false_and_request_provenance(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_post(url, **kwargs):
        captured.update({"url": url, **kwargs})
        return httpx.Response(
            200,
            headers={"x-request-id": "req-safe"},
            json={
                "id": "resp-safe",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Safe response"}],
                    }
                ],
                "usage": {"total_tokens": 12},
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(settings, "openai_api_key", SecretStr("sk-test-not-a-real-key"))
    monkeypatch.setattr("app.services.providers.openai_graph_chat.httpx.post", fake_post)
    response = OpenAIGraphChatProvider().respond(
        input_items=[{"role": "user", "content": "brainstorm"}],
        tools=graph_chat_tools(),
        instructions="bounded",
        metadata={"chat_session_id": "session"},
    )

    payload = captured["json"]
    assert payload["store"] is False
    assert "previous_response_id" not in payload
    assert all(tool["strict"] is True for tool in payload["tools"])
    assert all(tool["parameters"]["additionalProperties"] is False for tool in payload["tools"])
    assert response.response_id == "resp-safe"
    assert response.request_id == "req-safe"


def test_deepseek_adapter_translates_tool_loop_and_preserves_governance(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_post(url, **kwargs):
        captured.update({"url": url, **kwargs})
        return httpx.Response(
            200,
            headers={"x-request-id": "request-deepseek"},
            json={
                "id": "response-deepseek",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-deepseek",
                                    "type": "function",
                                    "function": {
                                        "name": "search_graph",
                                        "arguments": '{"query":"memory","limit":5}',
                                    },
                                }
                            ],
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 8,
                    "total_tokens": 20,
                },
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(settings, "deepseek_api_key", SecretStr("test-deepseek-key"))
    monkeypatch.setattr("app.services.providers.openai_graph_chat.httpx.post", fake_post)
    response = DeepSeekGraphChatProvider().respond(
        input_items=[
            {"role": "user", "content": "Find memory"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "prior-call",
                        "type": "function",
                        "function": {"name": "search_graph", "arguments": "{}"},
                    }
                ],
            },
            {"type": "function_call_output", "call_id": "prior-call", "output": "{}"},
        ],
        tools=graph_chat_tools(),
        instructions="bounded",
        metadata={"chat_session_id": "must-remain-local"},
    )

    payload = captured["json"]
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert payload["thinking"] == {"type": "disabled"}
    assert "metadata" not in payload
    assert payload["messages"][-1] == {
        "role": "tool",
        "tool_call_id": "prior-call",
        "content": "{}",
    }
    assert payload["tools"][0]["function"]["name"] == "search_graph"
    assert "publish_change_set" not in {item["function"]["name"] for item in payload["tools"]}
    assert response.tool_calls[0].arguments == {"query": "memory", "limit": 5}
    assert response.output_items[0]["role"] == "assistant"
    assert response.usage == {
        "input_tokens": 12,
        "output_tokens": 8,
        "total_tokens": 20,
    }


def test_graph_chat_provider_supports_deepseek_and_openai():
    assert graph_chat_provider("deepseek").name == "deepseek"
    assert graph_chat_provider("openai").name == "openai"
    with pytest.raises(DocumentError) as caught:
        graph_chat_provider("mistral")
    assert caught.value.code == "CHAT_PROVIDER_UNAVAILABLE"


def test_cloud_redaction_removes_credentials_and_contact_details():
    value = "Email owner@example.com, phone +1 (415) 555-0123, token sk-abcdefghijklmnop"
    redacted = redact_cloud_text(value)

    assert "owner@example.com" not in redacted
    assert "555-0123" not in redacted
    assert "sk-abcdefghijklmnop" not in redacted
    assert "[REDACTED_EMAIL]" in redacted


def test_reversible_cloud_redaction_uses_unique_ephemeral_markers():
    redactor = ReversibleCloudRedactor()
    redacted = redactor.redact("owner@example.com and backup@example.com, +84 901 234 567")

    assert "owner@example.com" not in redacted
    assert "backup@example.com" not in redacted
    assert redacted.count("[RS_REDACTED_EMAIL_") == 2
    assert redacted.count("[RS_REDACTED_PHONE_") == 1
    restored = redactor.restore(redacted, required_markers=redactor.markers)
    assert restored == "owner@example.com and backup@example.com, +84 901 234 567"

    with pytest.raises(ValueError):
        redactor.restore(
            redacted.replace(redactor.markers[0], ""),
            required_markers=redactor.markers,
        )


def test_document_scope_chat_uses_passage_retrieval_when_pgvector_enabled(db, monkeypatch):
    from types import SimpleNamespace

    from app.services import graph_chat as chat_module

    workspace, _ = create_document_evidence(db)
    research = db.get(ResearchItem, workspace.research_id)
    research.content = "first head passage. " + "ignored filler " * 200 + " tail answer passage"
    session = ChatSession(
        scope_type="document",
        scope_id=workspace.id,
        provider_name="openai",
        model_name="test-model",
    )
    db.add(session)
    db.flush()
    db.add(ChatMessage(session_id=session.id, role="user", content="where is the tail answer?"))
    db.commit()
    monkeypatch.setattr(settings, "vector_data_provider", "pgvector")
    monkeypatch.setattr(settings, "chat_document_scope_top_k_passages", 2)
    monkeypatch.setattr(settings, "chat_document_scope_passage_chars", 50)
    captured: dict[str, Any] = {}

    def fake_search_chunks(_self, _db, *, query, research_id, limit):
        captured["query"] = query
        captured["research_id"] = research_id
        captured["limit"] = limit
        return [
            ("chunk-tail", "tail answer passage truncated text", 0.1),
            ("chunk-head", "first head passage extra", 0.2),
        ]

    monkeypatch.setattr(chat_module.PgvectorProjection, "search_chunks", fake_search_chunks)
    # embedding_client_from_settings() requires a real API key; stub it so
    # the projection constructor never reaches the network.
    monkeypatch.setattr(chat_module, "embedding_client_from_settings", lambda: SimpleNamespace())

    context = build_scope_context(db, session)

    assert captured["research_id"] == research.id
    assert captured["limit"] == 2
    assert captured["query"] == "where is the tail answer?"
    passages = context["document_passages"]
    assert len(passages) == 2
    assert passages[0]["excerpt"].startswith("tail answer passage")
    assert context["document_text"].startswith("tail answer passage")
    assert "ignored filler" not in context["document_text"]


def test_document_scope_chat_falls_back_to_first_n_when_pgvector_disabled(db):
    workspace, _ = create_document_evidence(db)
    research = db.get(ResearchItem, workspace.research_id)
    research.content = "header passage " * 4000
    db.commit()
    session = ChatSession(
        scope_type="document",
        scope_id=workspace.id,
        provider_name="openai",
        model_name="test-model",
    )

    context = build_scope_context(db, session)

    assert settings.vector_data_provider != "pgvector"
    assert context["document_text"].startswith("header passage")
    assert context["document_text_truncated"] is True
    assert len(context["document_text"]) <= settings.chat_max_context_chars // 2
