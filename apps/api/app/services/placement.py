import re
import unicodedata

PILLAR_KEYWORDS: dict[str, dict[str, int]] = {
    "Business Problems & Outcomes": {
        "business value": 5,
        "outcome": 4,
        "cost": 4,
        "economics": 4,
        "roi": 4,
        "problem": 3,
    },
    "Business Context": {
        "organizational": 5,
        "business context": 5,
        "adoption": 4,
        "retail": 4,
        "sales": 4,
        "market": 3,
        "consumer": 3,
    },
    "Agent System Architecture": {
        "agent architecture": 6,
        "agent system": 5,
        "architecture": 4,
        "system design": 4,
        "orchestration": 3,
    },
    "Agent Capabilities & Workflows": {
        "coordination": 5,
        "agent workflow": 5,
        "agent capability": 5,
        "multi agent": 4,
        "planning": 3,
        "workflow": 2,
    },
    "Business Methods & Decision Intelligence": {
        "process mining": 6,
        "decision intelligence": 6,
        "business method": 5,
        "decision": 3,
        "automation opportunity": 3,
    },
    "Data, Knowledge & Memory": {
        "knowledge graph": 6,
        "agent memory": 6,
        "memory": 5,
        "vector retrieval": 5,
        "embedding": 3,
        "retrieval": 2,
        "data": 2,
    },
    "Tools, Functions & Integrations": {
        "tool calling": 6,
        "integration": 5,
        "agent tool": 5,
        "function calling": 5,
        "tool": 3,
    },
    "Outputs, Actions & Feedback": {
        "closed loop feedback": 6,
        "feedback": 5,
        "agent action": 4,
        "output": 4,
    },
    "Evaluation, Risk & Governance": {
        "human approval": 6,
        "risk control": 6,
        "agent evaluation": 6,
        "governance": 5,
        "auditability": 5,
        "policy engine": 5,
        "evaluating": 4,
        "risk": 4,
        "approval": 4,
    },
    "Engineering & Operations": {
        "workflow engine": 6,
        "event streaming": 6,
        "distributed tracing": 6,
        "observability": 5,
        "long running": 4,
        "operations": 3,
        "durable": 3,
    },
    "Research & Evidence": {
        "evaluation method": 6,
        "foundational survey": 6,
        "research evidence": 6,
        "benchmark": 5,
        "survey": 4,
        "scaling law": 4,
        "methodology": 4,
        "evidence": 3,
    },
}


def normalize_placement_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def rank_pillar_placements(text: str, limit: int = 3) -> list[tuple[str, float]]:
    normalized = normalize_placement_text(text)
    ranked: list[tuple[str, float]] = []
    for pillar, keywords in PILLAR_KEYWORDS.items():
        score = sum(weight for keyword, weight in keywords.items() if keyword in normalized)
        if score:
            ranked.append((pillar, float(score)))
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return ranked[: max(1, limit)]


def resolve_matched_pillars(
    title: str,
    content: str,
    proposed: list[str],
    canonical_pillars: list[str],
    *,
    limit: int = 3,
) -> list[str]:
    canonical = {pillar.casefold(): pillar for pillar in canonical_pillars}
    resolved: list[str] = []
    for item in proposed:
        pillar = canonical.get(item.casefold().strip())
        if pillar and pillar not in resolved:
            resolved.append(pillar)
    for pillar, _score in rank_pillar_placements(f"{title}\n{content[:4000]}", limit=limit):
        if pillar in canonical_pillars and pillar not in resolved:
            resolved.append(pillar)
    return resolved[:limit]
