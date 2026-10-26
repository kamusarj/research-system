import io
import zipfile
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from pypdf import PdfWriter
from sqlalchemy import select

from app.core.config import settings
from app.main import app
from app.models import (
    AIOutput,
    Attachment,
    AuditEvent,
    DocumentGraphEdge,
    DocumentGraphNode,
    DocumentGraphWorkspace,
    GraphChangeSet,
    IntakeReceipt,
    IntakeReceiptItem,
    KnowledgeNode,
    NodeEvidence,
    PaperEvaluation,
    ResearchItem,
)
from app.schemas.documents import DocumentGraphExtraction
from app.services.document_graph import ExtractedDocument, _extract_docx, _extract_pdf
from app.services.document_processing import (
    _complete_document_graph_with_recovery,
    run_pending_documents,
)
from app.services.documents import get_object_storage
from app.services.object_storage import DocumentError, LocalObjectStorage
from app.services.ocr import OCRPage, OCRResult


def use_storage(root: Path, max_bytes: int = 20_000_000) -> LocalObjectStorage:
    storage = LocalObjectStorage(root, max_bytes)
    app.dependency_overrides[get_object_storage] = lambda: storage
    return storage


def editable_docx() -> bytes:
    output = io.BytesIO()
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Governed agents</w:t></w:r></w:p>
    <w:p><w:r><w:t>Human review and durable memory improve reliable business agent
    decisions.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Evidence remains linked to every proposed graph
    change.</w:t></w:r></w:p>
  </w:body>
</w:document>"""
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document_xml)
    return output.getvalue()


class StructuredGraphProviderDouble:
    name = "structured-graph-provider-double"
    version = "test"

    def __init__(self, responses: list[dict]):
        self.responses = responses
        self.prompts: list[str] = []

    def complete_json(self, prompt, schema):
        self.prompts.append(prompt)
        response = self.responses[min(len(self.prompts) - 1, len(self.responses) - 1)]
        return schema.model_validate(response)


def valid_graph_response():
    return {
        "nodes": [
            {
                "local_id": "governed-agent",
                "node_type": "agent_pattern",
                "label": "Governed Agent",
                "evidence": [{"excerpt": "Human approval improves agent reliability."}],
            }
        ],
        "edges": [],
        "limitations": [],
    }


def invalid_graph_response():
    return {
        "nodes": valid_graph_response()["nodes"],
        "edges": [
            {
                "source_local_id": "governed-agent",
                "target_local_id": "missing-node",
                "edge_type": "depends_on",
            }
        ],
        "limitations": [],
    }


def test_structured_graph_validation_recovers_once_with_same_provider(caplog):
    caplog.set_level("INFO", logger="research-worker.documents")
    runtime = StructuredGraphProviderDouble([invalid_graph_response(), valid_graph_response()])
    extracted = ExtractedDocument(
        text="Human approval improves agent reliability.",
        sections=[],
    )

    result = _complete_document_graph_with_recovery(runtime, "Governed Agents", extracted, "job-1")

    assert isinstance(result, DocumentGraphExtraction)
    assert len(runtime.prompts) == 2
    assert "complete replacement object" in runtime.prompts[1]
    assert "value_error at graph" in runtime.prompts[1]
    assert "Structured document graph recovered" in caplog.text


def test_valid_structured_graph_does_not_retry():
    runtime = StructuredGraphProviderDouble([valid_graph_response()])
    extracted = ExtractedDocument(
        text="Human approval improves agent reliability.",
        sections=[],
    )

    result = _complete_document_graph_with_recovery(runtime, "Governed Agents", extracted, "job-2")

    assert len(result.nodes) == 1
    assert len(runtime.prompts) == 1


def test_structured_graph_recovery_keeps_terminal_validation_error(caplog):
    runtime = StructuredGraphProviderDouble([invalid_graph_response()])
    extracted = ExtractedDocument(
        text="Human approval improves agent reliability.",
        sections=[],
    )

    with pytest.raises(ValidationError):
        _complete_document_graph_with_recovery(runtime, "Governed Agents", extracted, "job-3")

    assert len(runtime.prompts) == 2
    assert "Structured document graph recovery failed" in caplog.text


def test_markdown_upload_persists_workspace_and_downloads_without_exposing_path(
    client, db, tmp_path
):
    use_storage(tmp_path)
    content = b"# Reliable agents\n\nHuman approval and durable memory."

    response = client.post(
        "/api/v1/documents",
        files={"file": ("reliable-agents.md", content, "text/markdown")},
    )

    assert response.status_code == 201, response.text
    document = response.json()
    assert document["filename"] == "reliable-agents.md"
    assert document["processing_status"] == "uploaded"
    assert document["review_status"] == "not_requested"
    assert document["size_bytes"] == len(content)
    assert len(document["content_hash"]) == 64
    assert "storage_object_key" not in document

    workspace = db.get(DocumentGraphWorkspace, document["id"])
    assert workspace is not None
    assert db.get(Attachment, workspace.attachment_id) is not None
    research = db.get(ResearchItem, workspace.research_id)
    assert research is not None
    assert research.status == "draft"
    assert research.collection_method == "upload"

    listing = client.get("/api/v1/documents").json()
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == document["id"]

    download = client.get(f"/api/v1/documents/{document['id']}/download")
    assert download.status_code == 200
    assert download.content == content
    assert "reliable-agents.md" in download.headers["content-disposition"]


def test_document_listing_exposes_bounded_summary_from_research_content(client, db, tmp_path):
    use_storage(tmp_path)
    created = client.post(
        "/api/v1/documents",
        files={"file": ("summary.md", b"# Summary", "text/markdown")},
    ).json()
    workspace = db.get(DocumentGraphWorkspace, created["id"])
    research = db.get(ResearchItem, workspace.research_id)
    research.content = "  Human\nreview   and durable memory improve reliable agent decisions.  "
    workspace.processing_status = "needs_review"
    db.commit()

    listing = client.get("/api/v1/documents")

    assert listing.status_code == 200
    assert listing.json()["items"][0]["summary"] == (
        "Human review and durable memory improve reliable agent decisions."
    )


def test_owner_deletes_inactive_document_and_owned_records(client, db, tmp_path):
    use_storage(tmp_path)
    created = client.post(
        "/api/v1/documents",
        files={"file": ("delete-me.md", b"# Delete me", "text/markdown")},
    ).json()
    workspace = db.get(DocumentGraphWorkspace, created["id"])
    research_id = workspace.research_id
    attachment_id = workspace.attachment_id
    workspace.processing_status = "needs_review"
    draft_change = GraphChangeSet(
        origin_type="document",
        origin_id=workspace.id,
        title="Draft document graph",
        lifecycle_status="draft",
    )
    db.add(draft_change)
    db.commit()

    response = client.delete(f"/api/v1/documents/{workspace.id}")

    assert response.status_code == 204, response.text
    db.expire_all()
    assert db.get(DocumentGraphWorkspace, created["id"]) is None
    assert db.get(Attachment, attachment_id) is None
    assert db.get(ResearchItem, research_id) is None
    assert db.get(GraphChangeSet, draft_change.id) is None
    assert [path for path in tmp_path.rglob("*") if path.is_file()] == []
    event = db.scalar(
        select(AuditEvent).where(
            AuditEvent.entity_id == created["id"],
            AuditEvent.action == "document.deleted",
        )
    )
    assert event is not None
    assert "content" not in event.payload


def test_document_delete_rejects_active_and_applied_graph_provenance(client, db, tmp_path):
    use_storage(tmp_path)
    created = client.post(
        "/api/v1/documents",
        files={"file": ("protected.md", b"# Protected", "text/markdown")},
    ).json()
    workspace = db.get(DocumentGraphWorkspace, created["id"])

    active = client.delete(f"/api/v1/documents/{workspace.id}")
    assert active.status_code == 409
    assert active.json()["error"]["code"] == "DOCUMENT_DELETE_IN_PROGRESS"

    workspace.processing_status = "needs_review"
    db.add(
        GraphChangeSet(
            origin_type="document",
            origin_id=workspace.id,
            title="Applied document graph",
            lifecycle_status="applied",
        )
    )
    db.commit()

    protected = client.delete(f"/api/v1/documents/{workspace.id}")
    assert protected.status_code == 409
    assert protected.json()["error"]["code"] == "DOCUMENT_DELETE_PROVENANCE_LOCKED"
    assert db.get(DocumentGraphWorkspace, workspace.id) is not None


def test_document_delete_preserves_intake_receipt_provenance(client, db, tmp_path):
    use_storage(tmp_path)
    created = client.post(
        "/api/v1/documents",
        files={"file": ("intake.md", b"# Intake", "text/markdown")},
    ).json()
    workspace = db.get(DocumentGraphWorkspace, created["id"])
    workspace.processing_status = "needs_review"
    receipt = IntakeReceipt(
        source_type="manual",
        source_namespace="test",
        external_occurrence_ref="occurrence-1",
        delivery_key_hash="d" * 64,
        submitted_by="test-user",
    )
    db.add(receipt)
    db.flush()
    db.add(
        IntakeReceiptItem(
            receipt_id=receipt.id,
            ordinal=1,
            kind="document",
            item_key_hash="i" * 64,
            document_workspace_id=workspace.id,
            initial_disposition="queued",
        )
    )
    db.commit()

    response = client.delete(f"/api/v1/documents/{workspace.id}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DOCUMENT_DELETE_PROVENANCE_LOCKED"
    assert db.get(DocumentGraphWorkspace, workspace.id) is not None


def test_upload_rejects_unsupported_mime_and_pdf_magic(client, tmp_path):
    use_storage(tmp_path)

    unsupported = client.post(
        "/api/v1/documents",
        files={"file": ("paper.docx", b"not a document", "application/octet-stream")},
    )
    fake_pdf = client.post(
        "/api/v1/documents",
        files={"file": ("paper.pdf", b"plain text", "application/pdf")},
    )

    assert unsupported.status_code == 415
    assert unsupported.json()["error"]["code"] == "UNSUPPORTED_DOCUMENT_TYPE"
    assert fake_pdf.status_code == 415
    assert fake_pdf.json()["error"]["code"] == "UNSUPPORTED_DOCUMENT_TYPE"
    assert [path for path in tmp_path.rglob("*") if path.is_file()] == []


def test_docx_upload_validates_openxml_and_extracts_ai_readable_content(client, db, tmp_path):
    storage = use_storage(tmp_path)
    content = editable_docx()

    created_response = client.post(
        "/api/v1/documents",
        files={
            "file": (
                "governed-agents.docx",
                content,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert created_response.status_code == 201, created_response.text
    created = created_response.json()
    assert run_pending_documents(db, storage=storage) == 1
    workspace = db.get(DocumentGraphWorkspace, created["id"])
    research = db.get(ResearchItem, workspace.research_id)
    assert workspace.processing_status == "needs_review"
    assert "Human review and durable memory" in research.content
    assert workspace.extracted_char_count == len(research.content)

    content_response = client.get(f"/api/v1/documents/{created['id']}/content")
    assert content_response.status_code == 200
    payload = content_response.json()
    assert payload["preview_kind"] == "docx"
    assert payload["supports_raw"] is True
    assert payload["editable"] is True
    assert payload["editing_representation"] == "extracted_text"
    assert payload["original_available"] is True
    assert payload["source_text"] == payload["extracted_text"]
    assert "Evidence remains linked" in payload["extracted_text"]


def test_docx_edit_versions_text_derivative_and_preserves_original_bytes(client, db, tmp_path):
    storage = use_storage(tmp_path)
    original_bytes = editable_docx()
    created = client.post(
        "/api/v1/documents",
        files={
            "file": (
                "governed-agents.docx",
                original_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    ).json()
    assert run_pending_documents(db, storage=storage) == 1
    workspace = db.get(DocumentGraphWorkspace, created["id"])
    attachment = db.get(Attachment, workspace.attachment_id)
    original_key = attachment.object_key
    initial_content = client.get(f"/api/v1/documents/{created['id']}/content").json()
    edited_text = initial_content["source_text"] + "\n\nResearcher correction."

    saved = client.post(
        f"/api/v1/documents/{created['id']}/versions",
        json={
            "base_version": 1,
            "content": edited_text,
            "change_summary": "Correct extracted content",
        },
    )

    assert saved.status_code == 201, saved.text
    assert saved.json()["version_number"] == 2
    db.refresh(workspace)
    db.refresh(attachment)
    assert workspace.storage_object_key.endswith(".md")
    assert attachment.object_key == original_key
    assert client.get(f"/api/v1/documents/{created['id']}/original").content == original_bytes
    assert client.get(f"/api/v1/documents/{created['id']}/download").content == original_bytes
    current = client.get(f"/api/v1/documents/{created['id']}/content").json()
    assert current["source_text"] == edited_text
    assert current["editing_representation"] == "extracted_text"

    assert run_pending_documents(db, storage=storage) == 1
    db.refresh(workspace)
    research = db.get(ResearchItem, workspace.research_id)
    assert workspace.processing_status == "needs_review"
    assert research.content == edited_text

    restored = client.post(
        f"/api/v1/documents/{created['id']}/versions/1/restore",
        json={"base_version": 2},
    )
    assert restored.status_code == 201, restored.text
    assert restored.json()["version_number"] == 3
    restored_content = client.get(f"/api/v1/documents/{created['id']}/content").json()
    assert "Researcher correction." not in restored_content["source_text"]
    assert client.get(f"/api/v1/documents/{created['id']}/original").content == original_bytes


def test_docx_rejects_zip_without_word_document(client, tmp_path):
    use_storage(tmp_path)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("not-a-document.txt", "not OpenXML")

    response = client.post(
        "/api/v1/documents",
        files={
            "file": (
                "invalid.docx",
                output.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_DOCUMENT_TYPE"
    assert [path for path in tmp_path.rglob("*") if path.is_file()] == []


def test_latex_raw_and_preview_content_feed_the_existing_ai_pipeline(client, db, tmp_path):
    storage = use_storage(tmp_path)
    source = (
        b"\\documentclass{article}\n"
        b"\\begin{document}\n"
        b"\\section{Agent evaluation}\n"
        b"A governed agent cites evidence before recommendations.\n"
        b"\\textbf{Human review} remains required.\n"
        b"\\end{document}\n"
    )
    created = client.post(
        "/api/v1/documents",
        files={"file": ("agent-evaluation.tex", source, "application/x-tex")},
    ).json()

    before_processing = client.get(f"/api/v1/documents/{created['id']}/content").json()
    assert before_processing["source_text"] == source.decode()
    assert before_processing["preview_kind"] == "latex"
    assert before_processing["supports_raw"] is True

    assert run_pending_documents(db, storage=storage) == 1
    workspace = db.get(DocumentGraphWorkspace, created["id"])
    research = db.get(ResearchItem, workspace.research_id)
    assert "\\documentclass" not in research.content
    assert "Agent evaluation" in research.content
    assert "Human review remains required." in research.content
    assert (
        client.get(f"/api/v1/documents/{created['id']}/content").json()["extracted_text"]
        == research.content
    )


def test_docx_extractor_preserves_heading_sections():
    extracted = _extract_docx(editable_docx(), "governed-agents.docx")

    assert extracted.sections[0].heading == "Governed agents"
    assert "durable memory" in extracted.text
    assert extracted.metadata["source_markup"] == "openxml"


def test_upload_enforces_streaming_size_limit(client, tmp_path):
    use_storage(tmp_path, max_bytes=8)

    response = client.post(
        "/api/v1/documents",
        files={"file": ("large.txt", b"123456789", "text/plain")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "DOCUMENT_TOO_LARGE"
    assert [path for path in tmp_path.rglob("*") if path.is_file()] == []


def test_duplicate_content_is_rejected_and_new_object_is_removed(client, tmp_path):
    use_storage(tmp_path)
    content = b"same governed knowledge"

    first = client.post(
        "/api/v1/documents",
        files={"file": ("first.txt", content, "text/plain")},
    )
    duplicate = client.post(
        "/api/v1/documents",
        files={"file": ("second.txt", content, "text/plain")},
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_DOCUMENT"
    stored_files = [path for path in tmp_path.rglob("*") if path.is_file()]
    assert len(stored_files) == 1


def test_worker_extracts_evaluates_and_builds_isolated_evidence_graph(client, db, tmp_path):
    storage = use_storage(tmp_path)
    content = (
        b"# Governed agent architecture\n\n"
        b"Human approval and durable memory improve reliable business agent workflows. "
        b"The evaluation measures decision quality and operational risk."
    )
    created = client.post(
        "/api/v1/documents",
        files={"file": ("governed-agents.md", content, "text/markdown")},
    ).json()

    assert run_pending_documents(db, storage=storage) == 1

    workspace = db.get(DocumentGraphWorkspace, created["id"])
    assert workspace is not None
    assert workspace.processing_status == "needs_review"
    assert workspace.review_status == "needs_review"
    assert workspace.extracted_char_count > 80
    assert workspace.model_name == "deterministic-test-provider"
    research = db.get(ResearchItem, workspace.research_id)
    assert research is not None
    assert "Human approval" in research.content

    evaluation = db.query(PaperEvaluation).filter_by(workspace_id=workspace.id).one()
    assert evaluation.fit_score == 77.75
    assert evaluation.decision == "draft_graph"
    assert evaluation.provider_name == "mistral"
    nodes = db.query(DocumentGraphNode).filter_by(workspace_id=workspace.id).all()
    edges = db.query(DocumentGraphEdge).filter_by(workspace_id=workspace.id).all()
    assert {node.node_type for node in nodes} >= {"document", "section", "agent_pattern"}
    assert edges == []
    ai_node = next(node for node in nodes if node.node_type == "agent_pattern")
    assert ai_node.evidence_status == "supported"
    assert db.query(NodeEvidence).filter_by(owner_id=ai_node.id).count() == 1

    detail = client.get(f"/api/v1/documents/{workspace.id}").json()
    assert detail["evaluation"]["fit_score"] == 77.75
    assert detail["graph_node_count"] == len(nodes)
    graph = client.get(f"/api/v1/documents/{workspace.id}/graph")
    assert graph.status_code == 200
    assert graph.json()["meta"]["node_count"] == len(nodes)
    assert any(item["evidence"] for item in graph.json()["nodes"])
    assert all(len(item["summary"]) <= 200 for item in graph.json()["nodes"])
    ai_node_payload = next(item for item in graph.json()["nodes"] if item["id"] == ai_node.id)
    assert 150 <= len(ai_node_payload["summary"]) <= 200


@pytest.mark.parametrize("skip_low_fit", [True, False])
def test_low_fit_readable_document_still_builds_isolated_graph(
    client, db, tmp_path, monkeypatch, skip_low_fit
):
    monkeypatch.setattr(settings, "document_graph_skip_low_fit", skip_low_fit)
    calls: list[str] = []

    class LowFitGraphProvider:
        name = "low-fit-graph-provider"
        version = "test"

        def complete_json(self, prompt, schema):
            calls.append(schema.__name__)
            if schema.__name__ == "PaperFitProviderAssessment":
                return schema.model_validate(
                    {
                        "dimensions": {
                            "system_fit": 20,
                            "business_applicability": 15,
                            "evidence_quality": 25,
                            "novelty": 20,
                            "implementation_value": 10,
                            "gap_coverage": 10,
                            "freshness": 20,
                        },
                        "detected_language": "en",
                        "reasoning_summary": "Readable but outside the core system scope.",
                        "confidence": 0.8,
                    }
                )
            return schema.model_validate(
                {
                    "nodes": [
                        {
                            "local_id": "outside-topic",
                            "node_type": "concept",
                            "label": "Outside topic",
                            "summary": (
                                "A readable source concept remains available for isolated analysis "
                                "even when its paper-fit score is too low for canonical promotion."
                            ),
                            "confidence": 0.7,
                            "evidence": [{"excerpt": "Readable source about an outside topic."}],
                        }
                    ],
                    "edges": [],
                    "limitations": [],
                }
            )

    storage = use_storage(tmp_path)
    monkeypatch.setattr(
        "app.services.document_processing.provider", lambda _name=None, **_kw: LowFitGraphProvider()
    )
    created = client.post(
        "/api/v1/documents",
        files={
            "file": (
                "outside-topic.md",
                b"# Outside topic\n\nReadable source about an outside topic.",
                "text/markdown",
            )
        },
    ).json()

    assert run_pending_documents(db, storage=storage) == 1

    evaluation = db.query(PaperEvaluation).filter_by(workspace_id=created["id"]).one()
    assert evaluation.fit_score < 40
    assert evaluation.decision == "not_relevant"
    # The isolated graph always exists; only the semantic AI extraction is optional.
    assert db.query(DocumentGraphNode).filter_by(workspace_id=created["id"]).count() >= 2
    workspace = db.get(DocumentGraphWorkspace, created["id"])
    codes = {item["code"] for item in workspace.extraction_limitations}
    if skip_low_fit:
        assert calls == ["PaperFitProviderAssessment"]
        assert "GRAPH_SEMANTIC_SKIPPED_LOW_FIT" in codes
    else:
        assert calls == ["PaperFitProviderAssessment", "DocumentGraphExtraction"]
        assert "GRAPH_SEMANTIC_SKIPPED_LOW_FIT" not in codes


def test_ai_research_compares_document_nodes_and_prepares_governed_change_set(client, db, tmp_path):
    storage = use_storage(tmp_path)
    created = client.post(
        "/api/v1/documents",
        files={
            "file": (
                "governed-agents.md",
                (
                    b"# Governed agents\n\nHuman approval and durable memory improve reliable "
                    b"business agent decisions with traceable evidence."
                ),
                "text/markdown",
            )
        },
    ).json()
    assert run_pending_documents(db, storage=storage) == 1
    semantic = (
        db.query(DocumentGraphNode)
        .filter(
            DocumentGraphNode.workspace_id == created["id"],
            DocumentGraphNode.node_type == "agent_pattern",
        )
        .one()
    )
    canonical_before = db.query(KnowledgeNode).count()

    response = client.post(
        f"/api/v1/documents/{created['id']}/graph/research",
        json={"node_ids": [semantic.id], "create_change_set": True},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    researched = next(item for item in payload["graph"]["nodes"] if item["id"] == semantic.id)
    assert researched["ai_research"]["comparison_status"] == "different"
    assert "bounded actions" in researched["ai_research"]["difference_summary"]
    assert payload["change_set"]["lifecycle_status"] == "draft"
    mutation = next(
        item
        for item in payload["change_set"]["mutations"]
        if item["proposed_json"].get("source_node_id") == semantic.id
    )
    assert mutation["proposed_json"]["ai_research"]["comparison_status"] == "different"
    assert "AI research:" in mutation["proposed_json"]["description"]
    assert db.query(KnowledgeNode).count() == canonical_before
    assert db.query(AIOutput).filter_by(task="document-node-research").count() == 1


def test_textless_pdf_routes_to_hard_gate_without_calling_ai(client, db, tmp_path):
    storage = use_storage(tmp_path)
    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(output)
    created = client.post(
        "/api/v1/documents",
        files={"file": ("scan.pdf", output.getvalue(), "application/pdf")},
    ).json()

    assert run_pending_documents(db, storage=storage) == 1

    workspace = db.get(DocumentGraphWorkspace, created["id"])
    evaluation = db.query(PaperEvaluation).filter_by(workspace_id=created["id"]).one()
    assert workspace is not None
    assert workspace.processing_status == "needs_review"
    assert workspace.model_name is None
    assert evaluation.fit_score is None
    assert evaluation.decision == "hard_gate_failed"
    assert {"readable_content", "content_valid"} <= set(evaluation.failed_gates)
    assert workspace.extraction_limitations[0]["code"] == "PDF_SCANNED_OCR_DISABLED"
    assert db.query(DocumentGraphNode).count() == 0


def test_uploaded_scanned_pdf_uses_shared_ocr_provenance(monkeypatch):
    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(output)
    monkeypatch.setattr(
        "app.services.document_graph.ocr_pdf",
        lambda _content: OCRResult(
            pages=[OCRPage(page=1, text="Recovered OCR evidence for document graph review.")],
            total_pages=1,
            pages_attempted=1,
        ),
    )

    extracted = _extract_pdf(output.getvalue())

    assert extracted.text.startswith("Recovered OCR evidence")
    assert extracted.sections[0].page == 1
    assert extracted.metadata["has_text_layer"] is False
    assert extracted.metadata["ocr_applied"] is True


def test_provider_transport_failure_is_typed_and_retry_scheduled(client, db, tmp_path, monkeypatch):
    storage = use_storage(tmp_path)
    created = client.post(
        "/api/v1/documents",
        files={
            "file": (
                "retry.txt",
                b"Business agent evaluation content with enough grounded details for evaluation.",
                "text/plain",
            )
        },
    ).json()

    class UnavailableProvider:
        name = "unavailable"
        version = "test"

        def complete_json(self, prompt, schema):
            raise httpx.ConnectError("offline")

    monkeypatch.setattr(
        "app.services.document_processing.provider", lambda _name=None, **_kw: UnavailableProvider()
    )
    assert run_pending_documents(db, storage=storage) == 1

    workspace = db.get(DocumentGraphWorkspace, created["id"])
    assert workspace is not None
    assert workspace.processing_status == "queued"
    assert workspace.error_code == "AI_PROVIDER_UNAVAILABLE"
    assert workspace.next_attempt_at is not None


def test_remote_storage_unavailable_is_typed_and_retry_scheduled(client, db, tmp_path):
    use_storage(tmp_path)
    created = client.post(
        "/api/v1/documents",
        files={
            "file": (
                "storage-retry.txt",
                b"Business agent content stored before a transient remote storage failure.",
                "text/plain",
            )
        },
    ).json()

    class UnavailableStorage:
        async def open(self, _key):
            if False:
                yield b""
            raise DocumentError(
                "DOCUMENT_STORAGE_FAILED", "Stored document is temporarily unavailable", 503
            )

    assert run_pending_documents(db, storage=UnavailableStorage()) == 1

    workspace = db.get(DocumentGraphWorkspace, created["id"])
    assert workspace is not None
    assert workspace.processing_status == "queued"
    assert workspace.error_code == "DOCUMENT_STORAGE_FAILED"
    assert workspace.next_attempt_at is not None


def test_analyze_and_retry_endpoints_enforce_workspace_state(client, db, tmp_path):
    use_storage(tmp_path)
    created = client.post(
        "/api/v1/documents",
        files={"file": ("state.txt", b"stateful document", "text/plain")},
    ).json()

    queued = client.post(f"/api/v1/documents/{created['id']}/analyze")
    conflict = client.post(f"/api/v1/documents/{created['id']}/retry")

    assert queued.status_code == 202
    assert queued.json()["processing_status"] == "queued"
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "DOCUMENT_STATE_CONFLICT"


def test_uploaded_html_original_is_never_rendered_inline(client, tmp_path):
    use_storage(tmp_path)
    created = client.post(
        "/api/v1/documents",
        files={
            "file": (
                "notes.html",
                b"<html><body><script>fetch('/api/v1/auth/users')</script>Notes</body></html>",
                "text/html",
            )
        },
    )
    assert created.status_code == 201, created.text

    original = client.get(f"/api/v1/documents/{created.json()['id']}/original?inline=true")
    download = client.get(f"/api/v1/documents/{created.json()['id']}/download")

    assert original.headers["content-disposition"].startswith("attachment;")
    assert original.headers["content-security-policy"].startswith("sandbox")
    assert download.headers["content-security-policy"].startswith("sandbox")
