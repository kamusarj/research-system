import json
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["AI_PROVIDER"] = "mistral"
os.environ["API_TRUSTED_HOSTS"] = "testserver"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.runtime_controls import rate_limiter
from app.db import Base, get_db
from app.main import app
from app.services.ai import EnrichmentResult, enrichment_prompt


class DeterministicTestProvider:
    name = "deterministic-test-provider"
    version = "test"

    def complete_json(self, prompt, schema):
        if schema.__name__ == "DocumentGraphResearchExtraction":
            node_context = json.loads(prompt.split("NODES:\n", 1)[1])
            return schema.model_validate(
                {
                    "results": [
                        {
                            "node_id": item["node_id"],
                            "research_summary": (
                                "Independent AI research confirms that governed business agents "
                                "combine explicit human approval, durable operational memory, "
                                "traceable evidence and bounded actions to improve reliable "
                                "decisions."
                            ),
                            "comparison_status": "different",
                            "difference_summary": (
                                "The document emphasizes approval, while independent research also "
                                "requires bounded actions and operational traceability."
                            ),
                            "confidence": 0.82,
                        }
                        for item in node_context
                    ]
                }
            )
        content = prompt.rsplit("Content:", 1)[-1] if "Content:" in prompt else prompt
        evidence_excerpt = " ".join(content.split())[:80] or "No readable source content"
        values = {
            "summary": " ".join(content.split())[:280] or "No readable source content",
            "concepts": ["Business Agent"],
            "tags": ["business-agent"],
            "technologies": ["LangGraph"] if "langgraph" in content.lower() else [],
            "agent_patterns": ["RAG"] if "rag" in content.lower() else [],
            "business_domains": (
                ["Customer Service"] if "customer service" in content.lower() else []
            ),
            "relations": [],
            "content_type": (
                "repository"
                if "Source type: github" in prompt
                else "paper"
                if "Source type: paper" in prompt or "Source type: pdf" in prompt
                else "article"
            ),
            "language": "en",
            "relevance_score": 75.0,
            "confidence": 0.65,
            "reasoning": "Deterministic test classification.",
            "dimensions": {
                "system_fit": 85,
                "business_applicability": 80,
                "evidence_quality": 75,
                "novelty": 70,
                "implementation_value": 80,
                "gap_coverage": 70,
                "freshness": 75,
            },
            "detected_language": "en",
            "matched_pillars": ["Agent System Architecture"],
            "candidate_parents": ["Multi-agent architecture"],
            "contribution_types": ["architecture"],
            "overlaps_with": [],
            "fills_gaps": [],
            "limitations": [],
            "reasoning_summary": "Grounded deterministic paper-fit assessment.",
            "nodes": [
                {
                    "local_id": "governed-agent",
                    "node_type": "agent_pattern",
                    "label": "Governed Agent",
                    "summary": (
                        "A governed business-agent pattern combines explicit human approval, "
                        "durable operational memory and traceable evidence so important automated "
                        "decisions remain reviewable and reliable."
                    ),
                    "parent_local_id": None,
                    "confidence": 0.9,
                    "evidence": [{"excerpt": evidence_excerpt}],
                }
            ],
            "edges": [],
            "replacement_text": "AI revised the selected passage with clearer wording.",
            "explanation": "Improved clarity while preserving the original intent.",
        }
        return schema.model_validate(
            {key: value for key, value in values.items() if key in schema.model_fields}
        )

    def enrich(self, title: str, content: str) -> EnrichmentResult:
        return self.complete_json(enrichment_prompt(title, content), EnrichmentResult)


@pytest.fixture(autouse=True)
def deterministic_ai(monkeypatch):
    rate_limiter.clear()
    runtime = DeterministicTestProvider()
    monkeypatch.setattr("app.services.ai.provider", lambda _name=None: runtime)
    monkeypatch.setattr("app.services.ingestion.provider", lambda _name=None: runtime)
    monkeypatch.setattr("app.services.document_processing.provider", lambda _name=None: runtime)
    monkeypatch.setattr("app.services.document_graph_research.provider", lambda _name=None: runtime)
    monkeypatch.setattr("app.services.document_editing.provider", lambda _name=None: runtime)
    yield
    rate_limiter.clear()


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db: Session) -> TestClient:
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.state.auth_session_factory = sessionmaker(bind=db.get_bind())
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    del app.state.auth_session_factory
