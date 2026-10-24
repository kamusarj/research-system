from app.models import (
    Attachment,
    ConceptAlias,
    DocumentGraphEdge,
    DocumentGraphNode,
    DocumentGraphWorkspace,
    GraphChangeSet,
    GraphMutation,
    KnowledgeEdge,
    KnowledgeNode,
    NodeEvidence,
    PaperEvaluation,
    ResearchItem,
)
from app.services.ontology import ensure_seed_ontology, ontology_id
from app.services.ontology_mapping import ontology_candidates


def create_reviewable_workspace(db, *, with_evidence: bool = True):
    ensure_seed_ontology(db)
    parent_id = ontology_id("data-knowledge-memory")
    existing = KnowledgeNode(
        node_type="Concept",
        canonical_label="Agent Memory",
        normalized_key="agent-memory",
        description="Canonical memory concept",
        primary_parent_id=parent_id,
        lifecycle_status="approved",
        created_by_type="human",
    )
    db.add(existing)
    db.flush()
    db.add(
        ConceptAlias(
            knowledge_node_id=existing.id,
            alias="AI Memory",
            normalized_alias="ai-memory",
            language="en",
            lifecycle_status="approved",
            created_by_type="human",
        )
    )
    research = ResearchItem(
        title="Grounded agent systems",
        type="reference",
        status="draft",
        collection_method="upload",
        content="AI Memory uses a Vector Database for durable retrieval.",
        authors=[],
        metadata_json={},
    )
    db.add(research)
    db.flush()
    attachment = Attachment(
        research_id=research.id,
        filename="agents.md",
        object_key=f"tests/{research.id}.md",
        mime_type="text/markdown",
        size_bytes=80,
    )
    db.add(attachment)
    db.flush()
    workspace = DocumentGraphWorkspace(
        research_id=research.id,
        attachment_id=attachment.id,
        storage_object_key=attachment.object_key,
        content_hash="a" * 64,
        processing_status="needs_review",
        review_status="needs_review",
        extraction_limitations=[],
        provider_name="mistral",
        model_name="test-model",
        extracted_char_count=len(research.content),
    )
    db.add(workspace)
    db.flush()
    db.add(
        PaperEvaluation(
            workspace_id=workspace.id,
            rubric_version="v1",
            dimension_scores={},
            fit_score=75,
            decision="draft_graph",
            failed_gates=[],
            matched_pillars=["Data, Knowledge & Memory"],
            candidate_parents=[],
            contribution_types=[],
            overlaps_with=[],
            fills_gaps=[],
            limitations=[],
            reasoning_summary="Relevant",
            confidence=0.9,
        )
    )
    memory = DocumentGraphNode(
        workspace_id=workspace.id,
        local_key="ai-memory",
        node_type="concept",
        label="AI Memory",
        summary="Durable agent memory",
        confidence=0.9,
        evidence_status="supported" if with_evidence else "evidence_pending",
        metadata_json={},
    )
    vector = DocumentGraphNode(
        workspace_id=workspace.id,
        local_key="vector-database",
        node_type="technology",
        label="Vector Database",
        summary="Retrieval storage technology",
        confidence=0.88,
        evidence_status="supported" if with_evidence else "evidence_pending",
        metadata_json={},
    )
    db.add_all([memory, vector])
    db.flush()
    edge = DocumentGraphEdge(
        workspace_id=workspace.id,
        source_node_id=memory.id,
        target_node_id=vector.id,
        edge_type="USES_TECH",
        confidence=0.86,
        evidence_status="supported" if with_evidence else "evidence_pending",
        metadata_json={},
    )
    db.add(edge)
    db.flush()
    if with_evidence:
        for owner_kind, owner_id, excerpt in [
            ("document_node", memory.id, "AI Memory"),
            ("document_node", vector.id, "Vector Database"),
            ("document_edge", edge.id, "AI Memory uses a Vector Database"),
        ]:
            db.add(
                NodeEvidence(
                    owner_kind=owner_kind,
                    owner_id=owner_id,
                    source_document_id=research.id,
                    location={"start_offset": 0},
                    excerpt=excerpt,
                    content_hash=workspace.content_hash,
                    extraction_method="test",
                    provenance={"workspace_id": workspace.id},
                )
            )
    db.commit()
    return workspace, existing


def test_candidate_retrieval_keeps_alias_and_similarity_as_candidates(db):
    _, existing = create_reviewable_workspace(db)

    exact = ontology_candidates(db, "AI Memory", node_type="Concept")
    similar = ontology_candidates(db, "Agent Memories", node_type="Concept")

    assert exact[0].node_id == existing.id
    assert exact[0].matched_by == "alias"
    assert exact[0].score == 1
    assert similar[0].node_id == existing.id
    assert similar[0].score < 1


def test_document_change_set_validates_applies_idempotently_and_compensates(client, db):
    workspace, existing = create_reviewable_workspace(db)

    created = client.post(f"/api/v1/documents/{workspace.id}/create-change-set")
    assert created.status_code == 201, created.text
    change_set = created.json()
    assert {item["operation"] for item in change_set["mutations"]} == {
        "ATTACH_EVIDENCE",
        "CREATE_NODE",
        "CREATE_EDGE",
    }
    assert client.post(
        f"/api/v1/graph/change-sets/{change_set['id']}/apply"
    ).status_code == 409

    validated = client.post(
        f"/api/v1/graph/change-sets/{change_set['id']}/validate"
    )
    assert validated.status_code == 200
    assert validated.json()["lifecycle_status"] == "needs_review"
    assert validated.json()["validation_summary"]["error_count"] == 0

    approved = client.post(f"/api/v1/graph/change-sets/{change_set['id']}/approve")
    assert approved.status_code == 200
    applied = client.post(f"/api/v1/graph/change-sets/{change_set['id']}/apply")
    repeated = client.post(f"/api/v1/graph/change-sets/{change_set['id']}/apply")
    assert applied.status_code == 200, applied.text
    assert repeated.status_code == 200
    assert applied.json()["lifecycle_status"] == "applied"
    assert repeated.json()["applied_at"] == applied.json()["applied_at"]

    vector = db.query(KnowledgeNode).filter_by(normalized_key="vector-database").one()
    assert vector.primary_parent_id == ontology_id("data-knowledge-memory")
    canonical_edge = db.query(KnowledgeEdge).filter_by(
        source_node_id=existing.id, target_node_id=vector.id, edge_type="USES_TECH"
    ).one()
    assert canonical_edge.lifecycle_status == "approved"
    assert db.query(NodeEvidence).filter_by(owner_id=existing.id).count() == 1
    assert db.query(NodeEvidence).filter_by(owner_id=vector.id).count() == 1
    db.refresh(workspace)
    assert workspace.review_status == "merged"

    compensation = client.post(
        f"/api/v1/graph/change-sets/{change_set['id']}/compensate"
    )
    assert compensation.status_code == 200
    undo_id = compensation.json()["id"]
    assert client.post(f"/api/v1/graph/change-sets/{undo_id}/approve").status_code == 200
    assert client.post(f"/api/v1/graph/change-sets/{undo_id}/apply").status_code == 200
    db.refresh(vector)
    db.refresh(canonical_edge)
    assert vector.lifecycle_status == "archived"
    assert canonical_edge.lifecycle_status == "superseded"


def test_evidence_pending_document_nodes_block_change_set_approval(client, db):
    workspace, _ = create_reviewable_workspace(db, with_evidence=False)
    change_set = client.post(
        f"/api/v1/documents/{workspace.id}/create-change-set"
    ).json()

    validated = client.post(
        f"/api/v1/graph/change-sets/{change_set['id']}/validate"
    ).json()
    approved = client.post(f"/api/v1/graph/change-sets/{change_set['id']}/approve")

    assert validated["lifecycle_status"] == "draft"
    assert validated["validation_summary"]["error_count"] == 3
    assert approved.status_code == 409
    assert approved.json()["error"]["code"] == "CHANGE_SET_CONFLICT"


def test_mutation_can_be_rejected_before_bulk_approval(client, db):
    workspace, _ = create_reviewable_workspace(db)
    change_set = client.post(
        f"/api/v1/documents/{workspace.id}/create-change-set"
    ).json()
    edge = next(item for item in change_set["mutations"] if item["operation"] == "CREATE_EDGE")

    decision = client.post(
        f"/api/v1/graph/change-sets/{change_set['id']}/mutations/{edge['id']}/decision",
        json={"decision": "rejected"},
    )
    approved = client.post(f"/api/v1/graph/change-sets/{change_set['id']}/approve")
    applied = client.post(f"/api/v1/graph/change-sets/{change_set['id']}/apply")

    assert decision.status_code == 200
    assert approved.status_code == 200
    assert applied.status_code == 200
    assert db.query(KnowledgeEdge).count() == 0
    db.refresh(workspace)
    assert workspace.review_status == "partially_merged"


def test_terminal_change_sets_cannot_be_reopened_or_reapproved(client, db):
    workspace, _ = create_reviewable_workspace(db)
    rejected = client.post(f"/api/v1/documents/{workspace.id}/create-change-set").json()
    assert client.post(f"/api/v1/graph/change-sets/{rejected['id']}/reject").status_code == 200

    revalidated = client.post(f"/api/v1/graph/change-sets/{rejected['id']}/validate")
    reapproved = client.post(f"/api/v1/graph/change-sets/{rejected['id']}/approve")

    assert revalidated.json()["lifecycle_status"] == "rejected"
    assert reapproved.status_code == 409

    db.refresh(workspace)
    workspace.review_status = "needs_review"
    db.commit()
    applied = client.post(f"/api/v1/documents/{workspace.id}/create-change-set").json()
    assert client.post(f"/api/v1/graph/change-sets/{applied['id']}/approve").status_code == 200
    assert client.post(f"/api/v1/graph/change-sets/{applied['id']}/apply").status_code == 200

    approve_again = client.post(f"/api/v1/graph/change-sets/{applied['id']}/approve")
    after = client.post(f"/api/v1/graph/change-sets/{applied['id']}/validate")

    assert approve_again.status_code == 409
    assert after.json()["lifecycle_status"] == "applied"


def test_recreating_an_archived_node_fails_validation_instead_of_apply(client, db):
    workspace, _ = create_reviewable_workspace(db)
    first = client.post(f"/api/v1/documents/{workspace.id}/create-change-set").json()
    assert client.post(f"/api/v1/graph/change-sets/{first['id']}/approve").status_code == 200
    assert client.post(f"/api/v1/graph/change-sets/{first['id']}/apply").status_code == 200
    undo = client.post(f"/api/v1/graph/change-sets/{first['id']}/compensate").json()
    assert client.post(f"/api/v1/graph/change-sets/{undo['id']}/approve").status_code == 200
    assert client.post(f"/api/v1/graph/change-sets/{undo['id']}/apply").status_code == 200
    original = next(item for item in first["mutations"] if item["operation"] == "CREATE_NODE")

    # A later proposal of the same concept, both with the deterministic ID and a fresh one.
    results = []
    for target_id in (original["target_id"], None):
        proposal = GraphChangeSet(origin_type="chat", title="Propose again")
        db.add(proposal)
        db.flush()
        db.add(
            GraphMutation(
                change_set_id=proposal.id,
                mutation_order=1,
                operation="CREATE_NODE",
                target_kind="node",
                target_id=target_id or "00000000-0000-4000-8000-000000000001",
                proposed_json=original["proposed_json"],
            )
        )
        db.commit()
        results.append(
            client.post(f"/api/v1/graph/change-sets/{proposal.id}/validate").json()
        )

    for validated in results:
        codes = {
            message["code"]
            for mutation in validated["mutations"]
            for message in mutation["validation_messages"]
        }
        assert "ARCHIVED_NODE_EXISTS" in codes
        assert validated["lifecycle_status"] == "draft"


def test_update_mutation_requires_known_lifecycle_status(client, db):
    workspace, existing = create_reviewable_workspace(db)
    change_set = client.post(f"/api/v1/documents/{workspace.id}/create-change-set").json()
    mutation = change_set["mutations"][0]
    stored = db.get(GraphMutation, mutation["id"])
    stored.operation = "UPDATE_NODE"
    stored.target_id = existing.id
    db.commit()

    decided = client.post(
        f"/api/v1/graph/change-sets/{change_set['id']}/mutations/{mutation['id']}/decision",
        json={"decision": "accepted", "proposed_json": {"lifecycle_status": "banana"}},
    )

    assert decided.status_code == 200
    assert decided.json()["validation_status"] == "error"
    approved = client.post(f"/api/v1/graph/change-sets/{change_set['id']}/approve")
    assert approved.status_code == 409
