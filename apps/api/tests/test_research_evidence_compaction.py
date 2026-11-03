import json

from app.services.research_agent.evidence import EntailmentWindow, compact_entailment_payload


def test_shared_context_preserves_every_original_window_and_quote():
    text = "Verified source sentence with useful factual context. " * 40
    windows = [
        EntailmentWindow(f"C{i}", "source", f"Claim {i}", "source sentence", i * 20, i * 20 + 600)
        for i in range(6)
    ]
    payload = compact_entailment_payload(windows, {"source": text})
    grouped = json.loads(payload)
    assert len(grouped["claims"]) == len(windows)
    assert {row["claim_id"] for row in grouped["claims"]} == {row.claim_id for row in windows}
    assert all(row["quote"] == "source sentence" for row in grouped["claims"])
    assert all(
        any(text[row.start : row.end] in passage for passage in grouped["evidence"])
        for row in windows
    )
    old = "\n".join(
        json.dumps(
            {"claim_id": row.claim_id, "claim": row.claim, "evidence": text[row.start : row.end]}
        )
        for row in windows
    )
    assert len(payload) < len(old) * 0.5


def test_compaction_never_combines_sources_or_invents_text_between_passages():
    text = "A " * 100 + "private gap " * 100 + "B " * 100
    windows = [
        EntailmentWindow("C1", "a", "first", "A", 0, 200),
        EntailmentWindow("C2", "a", "last", "B", len(text) - 200, len(text)),
        EntailmentWindow("C3", "b", "other source", "other", 0, 5),
    ]
    payload = compact_entailment_payload(windows, {"a": text, "b": "other"})
    assert "private gap" not in payload
    rows = [json.loads(line) for line in payload.splitlines()]
    for row in rows:
        ids = {claim["claim_id"] for claim in row.get("claims", [row])}
        assert not ("C3" in ids and ids & {"C1", "C2"})


def test_single_claim_keeps_small_legacy_representation():
    window = EntailmentWindow("C1", "a", "short", "long quote " * 50, 0, 8)
    row = json.loads(compact_entailment_payload([window], {"a": "evidence"}))
    assert row == {"claim_id": "C1", "claim": "short", "evidence": "evidence"}
