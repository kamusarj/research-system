import io
import json

from pypdf import PdfWriter

from app.models import (
    AuditEvent,
    DocumentAIEditProposal,
    DocumentGraphNode,
    DocumentGraphWorkspace,
    DocumentSourceVersion,
    NodeEvidence,
    ResearchItem,
    SearchVectorProjection,
)
from app.services.document_processing import run_pending_documents
from app.services.document_rag import refresh_document_rag
from app.services.documents import get_object_storage
from app.services.object_storage import LocalObjectStorage


def use_storage(tmp_path):
    storage = LocalObjectStorage(tmp_path, 20_000_000)
    from app.main import app

    app.dependency_overrides[get_object_storage] = lambda: storage
    return storage


def upload_editable(client, db, tmp_path, content="# Title\n\nOriginal selected text."):
    storage = use_storage(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("editable.md", content.encode(), "text/markdown")},
    )
    assert response.status_code == 201, response.text
    workspace = db.get(DocumentGraphWorkspace, response.json()["id"])
    assert workspace is not None
    workspace.processing_status = "needs_review"
    workspace.review_status = "needs_review"
    db.commit()
    return response.json(), workspace, storage


def test_upload_creates_version_one_and_manual_save_restore_are_immutable(client, db, tmp_path):
    created, workspace, storage = upload_editable(client, db, tmp_path)

    versions = client.get(f"/api/v1/documents/{workspace.id}/versions")
    assert versions.status_code == 200
    assert [(item["version_number"], item["origin"]) for item in versions.json()["items"]] == [
        (1, "upload")
    ]
    original = db.query(DocumentSourceVersion).filter_by(workspace_id=workspace.id).one()
    original_bytes = b"".join(__import__("asyncio").run(_collect(storage, original.object_key)))

    saved = client.post(
        f"/api/v1/documents/{workspace.id}/versions",
        json={
            "base_version": 1,
            "content": "# Title\n\nManually updated source.",
            "change_summary": "Manual correction",
        },
    )
    assert saved.status_code == 201, saved.text
    assert saved.json()["version_number"] == 2
    db.refresh(workspace)
    assert workspace.processing_status == "uploaded"
    assert workspace.rag_status == "pending"
    assert workspace.source_version == 2
    retained_bytes = b"".join(__import__("asyncio").run(_collect(storage, original.object_key)))
    assert retained_bytes == original_bytes

    workspace.processing_status = "needs_review"
    db.commit()
    restored = client.post(
        f"/api/v1/documents/{workspace.id}/versions/1/restore",
        json={"base_version": 2},
    )
    assert restored.status_code == 201, restored.text
    assert restored.json()["version_number"] == 3
    assert restored.json()["origin"] == "restore"
    content = client.get(f"/api/v1/documents/{workspace.id}/content").json()
    assert content["source_text"] == "# Title\n\nOriginal selected text."


async def _collect(storage, key):
    return [chunk async for chunk in storage.open(key)]


def test_ai_edit_requires_explicit_accept_and_reject_is_non_mutating(client, db, tmp_path):
    created, workspace, _storage = upload_editable(client, db, tmp_path)
    source = client.get(f"/api/v1/documents/{workspace.id}/content").json()["source_text"]
    selected = "Original selected text."
    start = source.index(selected)

    proposed = client.post(
        f"/api/v1/documents/{workspace.id}/ai-edits",
        json={
            "base_version": 1,
            "selection_start": start,
            "selection_end": start + len(selected),
            "action": "improve",
        },
    )
    assert proposed.status_code == 201, proposed.text
    proposal = proposed.json()
    assert proposal["status"] == "draft"
    assert proposal["original_text"] == selected
    assert client.get(f"/api/v1/documents/{workspace.id}/content").json()["source_text"] == source

    accepted = client.post(f"/api/v1/documents/{workspace.id}/ai-edits/{proposal['id']}/accept")
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"
    assert accepted.json()["accepted_version_number"] == 2
    edited = client.get(f"/api/v1/documents/{workspace.id}/content").json()["source_text"]
    assert "AI revised the selected passage" in edited
    assert selected not in edited

    db.refresh(workspace)
    workspace.processing_status = "needs_review"
    db.commit()
    next_selected = "# Title"
    next_start = edited.index(next_selected)
    second_response = client.post(
        f"/api/v1/documents/{workspace.id}/ai-edits",
        json={
            "base_version": 2,
            "selection_start": next_start,
            "selection_end": next_start + len(next_selected),
            "action": "shorten",
        },
    )
    assert second_response.status_code == 201, second_response.text
    second = second_response.json()
    rejected = client.post(f"/api/v1/documents/{workspace.id}/ai-edits/{second['id']}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    db.refresh(workspace)
    assert workspace.source_version == 2


def test_ai_edit_stale_version_and_binary_source_fail_closed(client, db, tmp_path):
    _created, workspace, _storage = upload_editable(client, db, tmp_path)
    source = "# Title\n\nOriginal selected text."
    start = source.index("Original")
    proposal = client.post(
        f"/api/v1/documents/{workspace.id}/ai-edits",
        json={
            "base_version": 1,
            "selection_start": start,
            "selection_end": len(source),
            "action": "fix_grammar",
        },
    ).json()
    saved = client.post(
        f"/api/v1/documents/{workspace.id}/versions",
        json={"base_version": 1, "content": source + "\nNew line."},
    )
    assert saved.status_code == 201
    stale = client.post(f"/api/v1/documents/{workspace.id}/ai-edits/{proposal['id']}/accept")
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "DOCUMENT_VERSION_CONFLICT"

    latex = client.post(
        "/api/v1/documents",
        files={"file": ("editable.tex", b"\\section{Test}", "application/x-tex")},
    ).json()
    latex_workspace = db.get(DocumentGraphWorkspace, latex["id"])
    latex_workspace.processing_status = "needs_review"
    db.commit()
    saved_latex = client.post(
        f"/api/v1/documents/{latex['id']}/versions",
        json={"base_version": 1, "content": "\\section{Changed}"},
    )
    assert saved_latex.status_code == 201, saved_latex.text

    pdf_bytes = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(pdf_bytes)
    pdf = client.post(
        "/api/v1/documents",
        files={"file": ("read-only.pdf", pdf_bytes.getvalue(), "application/pdf")},
    ).json()
    pdf_workspace = db.get(DocumentGraphWorkspace, pdf["id"])
    pdf_workspace.processing_status = "needs_review"
    db.commit()
    denied = client.post(
        f"/api/v1/documents/{pdf['id']}/versions",
        json={"base_version": 1, "content": "Changed"},
    )
    assert denied.status_code == 409
    assert denied.json()["error"]["code"] == "DOCUMENT_NOT_EDITABLE"


class EmbeddingDouble:
    provider = "mistral"
    model = "mistral-embed-test"

    def embed(self, texts):
        return [[float(index == 0) for index in range(1024)] for _ in texts]


def test_document_rag_refreshes_draft_chunks_and_audit_is_content_safe(client, db, tmp_path):
    _created, workspace, _storage = upload_editable(
        client,
        db,
        tmp_path,
        content="# RAG\n\nA long grounded document passage for automatic retrieval.",
    )
    research = db.get(ResearchItem, workspace.research_id)
    research.content = "A long grounded document passage for automatic retrieval."
    db.commit()

    status = refresh_document_rag(db, workspace, embedding_factory=EmbeddingDouble)

    assert status.status == "ready"
    assert status.indexed_version == 1
    assert status.chunk_count >= 1
    assert db.query(SearchVectorProjection).filter_by(research_id=research.id).count() >= 1
    assert research.status == "draft"

    payloads = [
        event.payload
        for event in db.query(AuditEvent).filter(AuditEvent.entity_id == workspace.id).all()
    ]
    serialized = json.dumps(payloads)
    assert "grounded document passage" not in serialized
    assert db.query(DocumentAIEditProposal).count() == 0


def test_worker_automatically_refreshes_rag_after_extraction(client, db, tmp_path, monkeypatch):
    storage = use_storage(tmp_path)
    created = client.post(
        "/api/v1/documents",
        files={
            "file": (
                "automatic-rag.md",
                b"# Automatic RAG\n\nHuman-reviewed agent memory with grounded evidence.",
                "text/markdown",
            )
        },
    ).json()
    calls: list[str] = []
    uploaded_workspace = db.get(DocumentGraphWorkspace, created["id"])
    assert uploaded_workspace is not None
    stale_node = DocumentGraphNode(
        workspace_id=created["id"],
        local_key="stale-version-node",
        node_type="concept",
        label="Stale version evidence",
        summary="Must disappear before the new source is evaluated.",
        confidence=1,
        evidence_status="supported",
        metadata_json={},
    )
    db.add(stale_node)
    db.flush()
    db.add(
        NodeEvidence(
            owner_kind="document_node",
            owner_id=stale_node.id,
            source_document_id=uploaded_workspace.research_id,
            location={"start_offset": 0, "end_offset": 5},
            excerpt="stale",
            content_hash="old-version",
            extraction_method="test",
            provenance={"workspace_id": created["id"]},
        )
    )
    db.commit()
    stale_node_id = stale_node.id

    def fake_refresh(_db, workspace, **_kwargs):
        calls.append(workspace.id)
        workspace.rag_status = "ready"
        workspace.rag_chunk_count = 2
        workspace.rag_indexed_version = workspace.source_version

    monkeypatch.setattr("app.services.document_processing.refresh_document_rag", fake_refresh)

    assert run_pending_documents(db, storage=storage) == 1
    workspace = db.get(DocumentGraphWorkspace, created["id"])
    assert workspace is not None
    assert calls == [workspace.id]
    assert workspace.rag_status == "ready"
    assert workspace.rag_indexed_version == workspace.source_version
    assert db.get(DocumentGraphNode, stale_node_id) is None
    assert db.query(NodeEvidence).filter_by(owner_id=stale_node_id).count() == 0
