"""Reviewed research must have the same publication boundary through every editor."""

import hashlib

import pytest
from sqlalchemy.orm import Session

from app.core.config import settings
from app.main import app
from app.models import (
    Attachment,
    AuditEvent,
    DocumentAIEditProposal,
    DocumentGraphNode,
    DocumentGraphWorkspace,
    DocumentSourceVersion,
    GraphChangeSet,
    GraphMutation,
    KnowledgeEdge,
    KnowledgeNode,
    NodeEvidence,
    ResearchItem,
    ResearchRelation,
)
from app.schemas.auth import UserCreate
from app.services.auth import create_user
from app.services.documents import get_object_storage
from app.services.graph_changes import _copy_evidence
from app.services.object_storage import LocalObjectStorage


def _login(client, db, monkeypatch, role):
    monkeypatch.setattr(settings, "auth_mode", "local")
    monkeypatch.setattr(settings, "auth_cookie_secure", False)
    user = create_user(
        db,
        UserCreate(
            name="Synthetic reviewer",
            email=f"{role}@fixture.invalid",
            password="synthetic-review-password-123",
            role=role,
        ),
        actor="test-operator",
    )
    assert client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "synthetic-review-password-123"},
    ).status_code == 200
    return {"X-CSRF-Token": client.cookies.get(settings.auth_csrf_cookie_name)}


def _objects(root):
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*") if path.is_file()
    }


def _proposal(db, workspace, text):
    proposal = DocumentAIEditProposal(
        workspace_id=workspace.id,
        base_version_number=workspace.source_version,
        selection_start=0,
        selection_end=len(text),
        selected_text_hash=hashlib.sha256(text.encode()).hexdigest(),
        action="improve",
        replacement_text="Explicitly reviewed AI replacement.",
        explanation="Synthetic proposal",
        provider_name="ollama",
        model_name="synthetic-model",
        prompt_version="synthetic",
        status="draft",
    )
    db.add(proposal)
    return proposal


@pytest.fixture
def source_document(client, db, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "auth_mode", "disabled")
    storage = LocalObjectStorage(tmp_path, 20_000_000)
    app.dependency_overrides[get_object_storage] = lambda: storage
    created = client.post(
        "/api/v1/documents",
        files={"file": ("reviewed.md", b"Original reviewed source.", "text/markdown")},
    )
    assert created.status_code == 201, created.text
    workspace = db.get(DocumentGraphWorkspace, created.json()["id"])
    workspace.processing_status = "needs_review"
    db.commit()
    # Give restore a real historical version with different immutable bytes.
    saved = client.post(
        f"/api/v1/documents/{workspace.id}/versions",
        json={"base_version": 1, "content": "Current reviewed source."},
    )
    assert saved.status_code == 201, saved.text
    workspace.processing_status = "needs_review"
    db.commit()
    return workspace, storage


@pytest.mark.parametrize("operation", ["version", "restore", "ai_accept"])
@pytest.mark.parametrize(
    ("role", "research_status", "allowed"),
    [
        ("researcher", "approved", False),
        ("researcher", "in-review", False),
        ("researcher", "draft", True),
        ("owner", "approved", True),
        ("owner", "in-review", True),
    ],
)
def test_document_edits_obey_review_boundary_before_storage_or_db_writes(
    client, db, monkeypatch, source_document, operation, role, research_status, allowed
):
    workspace, storage = source_document
    research = db.get(ResearchItem, workspace.research_id)
    research.status = research_status
    proposal = None
    if operation == "ai_accept":
        proposal = _proposal(db, workspace, research.content)
    db.commit()
    headers = _login(client, db, monkeypatch, role)
    before_objects = _objects(storage.root)
    before_events = db.query(AuditEvent).count()
    writes = []
    original_put = storage.put

    async def put(*args, **kwargs):
        writes.append(True)
        return await original_put(*args, **kwargs)

    monkeypatch.setattr(storage, "put", put)
    prefix = f"/api/v1/documents/{workspace.id}"
    if operation == "version":
        response = client.post(
            prefix + "/versions",
            json={"base_version": 2, "content": "Explicitly reviewed manual replacement."},
            headers=headers,
        )
    elif operation == "restore":
        response = client.post(
            prefix + "/versions/1/restore", json={"base_version": 2}, headers=headers
        )
    else:
        response = client.post(prefix + f"/ai-edits/{proposal.id}/accept", headers=headers)
    db.refresh(workspace)
    db.refresh(research)
    assert research.status == research_status
    if allowed:
        assert response.status_code == (200 if operation == "ai_accept" else 201), response.text
        assert writes == [True]
        assert workspace.source_version == 3
        assert research.content != "Current reviewed source."
        if proposal is not None:
            db.refresh(proposal)
            assert proposal.status == "accepted"
    else:
        assert response.status_code == 403, response.text
        assert writes == []
        assert _objects(storage.root) == before_objects
        assert workspace.source_version == 2
        assert research.content == "Current reviewed source."
        assert db.query(DocumentSourceVersion).filter_by(workspace_id=workspace.id).count() == 2
        assert db.query(AuditEvent).count() == before_events
        if proposal is not None:
            db.refresh(proposal)
            assert proposal.status == "draft"


@pytest.mark.parametrize("operation", ["version", "restore", "ai_accept"])
def test_publication_during_storage_write_rechecks_status_and_cleans_unattached_object(
    client, db, monkeypatch, source_document, operation
):
    workspace, storage = source_document
    research_id = workspace.research_id
    proposal = (
        _proposal(db, workspace, db.get(ResearchItem, research_id).content)
        if operation == "ai_accept" else None
    )
    db.commit()
    headers = _login(client, db, monkeypatch, "researcher")
    before_objects = _objects(storage.root)
    before_events = db.query(AuditEvent).count()
    created, cleaned = [], []
    original_put, original_delete = storage.put, storage.delete

    async def publish_during_put(*args, **kwargs):
        stored = await original_put(*args, **kwargs)
        created.append(stored.key)
        with Session(db.get_bind()) as owner:
            owner.get(ResearchItem, research_id).status = "approved"
            owner.commit()
        return stored

    async def delete(key):
        cleaned.append(key)
        return await original_delete(key)

    monkeypatch.setattr(storage, "put", publish_during_put)
    monkeypatch.setattr(storage, "delete", delete)
    prefix = f"/api/v1/documents/{workspace.id}"
    if operation == "version":
        response = client.post(
            prefix + "/versions", json={"base_version": 2, "content": "Race replacement."},
            headers=headers,
        )
    elif operation == "restore":
        response = client.post(
            prefix + "/versions/1/restore", json={"base_version": 2}, headers=headers
        )
    else:
        response = client.post(prefix + f"/ai-edits/{proposal.id}/accept", headers=headers)
    assert response.status_code == 403, response.text
    assert len(created) == 1 and cleaned == created
    assert _objects(storage.root) == before_objects
    db.refresh(workspace)
    research = db.get(ResearchItem, research_id, populate_existing=True)
    assert workspace.source_version == 2
    assert research.status == "approved" and research.content == "Current reviewed source."
    assert db.query(DocumentSourceVersion).filter_by(workspace_id=workspace.id).count() == 2
    assert db.query(AuditEvent).count() == before_events
    if proposal is not None:
        db.refresh(proposal)
        assert proposal.status == "draft"


@pytest.mark.parametrize(
    ("role", "research_status", "allowed"),
    [
        ("researcher", "approved", False),
        ("researcher", "in-review", False),
        ("researcher", "draft", True),
        ("owner", "approved", True),
        ("owner", "in-review", True),
    ],
)
def test_attachment_metadata_obeys_review_boundary(
    client, db, monkeypatch, role, research_status, allowed
):
    item = ResearchItem(title="Attachments", type="reference", status=research_status)
    db.add(item)
    db.commit()
    headers = _login(client, db, monkeypatch, role)
    response = client.post(
        f"/api/v1/research/{item.id}/attachments",
        json={"filename": "fixture.md", "object_key": "synthetic/object.md",
              "mime_type": "text/markdown", "size_bytes": 10},
        headers=headers,
    )
    assert response.status_code == (201 if allowed else 403), response.text
    assert db.query(Attachment).filter_by(research_id=item.id).count() == int(allowed)


@pytest.mark.parametrize("role", ["owner", "researcher"])
@pytest.mark.parametrize(
    ("source_status", "target_status"),
    [
        ("approved", "approved"),
        ("approved", "draft"),
        ("draft", "approved"),
        ("in-review", "draft"),
        ("draft", "in-review"),
        ("draft", "draft"),
    ],
)
def test_relations_cannot_publish_or_edit_reviewed_endpoints_without_owner(
    client, db, monkeypatch, role, source_status, target_status
):
    items = [
        ResearchItem(title="Synthetic A", type="reference", status=source_status, content="A"),
        ResearchItem(title="Synthetic B", type="reference", status=target_status, content="B"),
    ]
    db.add_all(items)
    db.commit()
    headers = _login(client, db, monkeypatch, role)
    before_events = db.query(AuditEvent).count()
    response = client.post(
        f"/api/v1/research/{items[0].id}/relations",
        json={"target_id": items[1].id, "relation_type": "contradicts"},
        headers=headers,
    )
    allowed = role == "owner" or source_status == target_status == "draft"
    assert response.status_code == (201 if allowed else 403), response.text
    assert db.query(ResearchRelation).count() == int(allowed)
    if not allowed:
        assert db.query(AuditEvent).count() == before_events
    graph = client.get("/api/v1/graph").json()
    visible = any(edge["type"] == "CONTRADICTS" for edge in graph["edges"])
    assert visible == (allowed and source_status == target_status == "approved")


@pytest.mark.parametrize(
    ("retention", "blocked"),
    [
        ("canonical_node", True),
        ("canonical_edge", True),
        ("legacy_canonical", True),
        ("applied_alias", True),
        ("applied_source_node", True),
        ("draft_alias", False),
        ("rejected_alias", False),
    ],
)
def test_delete_preserves_all_canonical_and_applied_graph_evidence(
    client, db, monkeypatch, source_document, retention, blocked
):
    workspace, storage = source_document
    document_id, research_id = workspace.id, workspace.research_id
    local_node = DocumentGraphNode(
        workspace_id=workspace.id, local_key="source", node_type="concept", label="Source"
    )
    node = KnowledgeNode(
        node_type="concept", canonical_label="Retained concept", normalized_key="retained"
    )
    other = KnowledgeNode(
        node_type="concept", canonical_label="Other concept", normalized_key="other"
    )
    change = GraphChangeSet(
        origin_type="chat", origin_id="synthetic-chat", title="Reviewed source attachment",
        lifecycle_status="draft" if retention == "draft_alias" else "applied",
    )
    db.add_all([local_node, node, other, change])
    db.flush()
    evidence = NodeEvidence(
        owner_kind="document_node", owner_id=local_node.id,
        source_document_id=research_id, excerpt="Reviewed source quote.", content_hash="f" * 64,
        provenance={"workspace_id": document_id},
    )
    db.add(evidence)
    db.flush()
    if retention in {"canonical_node", "legacy_canonical"}:
        _copy_evidence(db, [evidence.id], "knowledge_node", node.id, change.id)
        db.flush()
        if retention == "legacy_canonical":
            copied = db.query(NodeEvidence).filter_by(owner_kind="knowledge_node").one()
            copied.source_document_id = None
    elif retention == "canonical_edge":
        edge = KnowledgeEdge(
            source_node_id=node.id, target_node_id=other.id, edge_type="SUPPORTS"
        )
        db.add(edge)
        db.flush()
        _copy_evidence(db, [evidence.id], "knowledge_edge", edge.id, change.id)
    else:
        db.add(GraphMutation(
            change_set_id=change.id, mutation_order=0, operation="ADD_ALIAS", target_kind="node",
            target_id=node.id, review_decision="rejected" if retention == "rejected_alias"
            else "accepted",
            proposed_json={"source_node_id": local_node.id} if retention == "applied_source_node"
            else {"alias": "Alias", "evidence_ids": [evidence.id]},
        ))
    db.commit()
    headers = _login(client, db, monkeypatch, "owner")
    before_objects = _objects(storage.root)
    before_evidence = db.query(NodeEvidence).count()
    deletes = []
    original_delete = storage.delete

    async def delete(key):
        deletes.append(key)
        return await original_delete(key)

    monkeypatch.setattr(storage, "delete", delete)
    response = client.delete(f"/api/v1/documents/{document_id}", headers=headers)
    if blocked:
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "DOCUMENT_DELETE_PROVENANCE_LOCKED"
        assert deletes == []
        assert _objects(storage.root) == before_objects
        assert db.query(NodeEvidence).count() == before_evidence
        assert db.get(DocumentGraphWorkspace, document_id) is not None
        assert db.get(ResearchItem, research_id) is not None
        assert not db.query(AuditEvent).filter_by(action="document.deleted").count()
    else:
        assert response.status_code == 204, response.text
        assert deletes
        assert _objects(storage.root) == {}
        db.expire_all()
        assert db.get(DocumentGraphWorkspace, document_id) is None
        assert db.get(ResearchItem, research_id) is None
    assert db.get(KnowledgeNode, node.id).lifecycle_status == "approved"
