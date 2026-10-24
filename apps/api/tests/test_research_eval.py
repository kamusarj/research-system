import json

from app.evaluation import research_agent as evaluation
from app.services.research_agent import runner
from tests.test_research_agent import FakeLLM, FakeSearch, fake_fetch_factory


def _advance(db, run):
    return runner.advance_research_run(
        db, run, llm=FakeLLM(), providers=[FakeSearch()], fetch=fake_fetch_factory()
    )


def test_eval_questions_are_well_formed():
    questions = evaluation.load_questions()
    assert 5 <= len(questions) <= 10
    assert len({q["id"] for q in questions}) == len(questions)
    assert all(q["question"] and q["key_entities"] for q in questions)


def test_eval_scores_runs_and_compares_variants(db, monkeypatch, tmp_path):
    monkeypatch.setattr(evaluation.settings, "research_agent_enabled", True)
    question = evaluation.load_questions(only={"q1-market-size"})[0]
    results = {}
    for variant in ("naive", "optimized"):
        scored = evaluation.run_question(db, question, variant, advance=_advance)
        assert scored["status"] == "completed"
        assert scored["citation_coverage"] == 1.0
        assert 0 < scored["quote_verification_rate"] < 1  # trích dẫn bịa của LLM giả bị loại
        results[variant] = {
            "variant": variant,
            "results": [scored],
            "summary": evaluation.summarize([scored]),
        }
    assert "EntailmentBatch" not in json.dumps(results)
    table = evaluation.compare_markdown(results["naive"], results["optimized"])
    assert "| citation_coverage | 1.0 | 1.0 |" in table
    assert "| Chỉ số | naive | optimized |" in table
    assert table.startswith("Câu hỏi so sánh: 1")


def test_cited_duplicate_rate_detects_reposted_sources():
    from app.models import ResearchRunSource

    text = "Agents " + " ".join(f"word{index}" for index in range(200))
    sources = [
        ResearchRunSource(citation_index=1, content_text=text),
        ResearchRunSource(citation_index=2, content_text=text + " updated"),
        ResearchRunSource(citation_index=3, content_text="other " * 200),
    ]
    assert evaluation.cited_duplicate_rate(sources) == round(1 / 3, 3)


def test_eval_runs_are_isolated_from_worker_and_from_each_others_cache(db, monkeypatch):
    from app.models import ResearchRun

    monkeypatch.setattr(evaluation.settings, "research_agent_enabled", True)
    question = evaluation.load_questions(only={"q2-customer-service"})[0]
    first = evaluation.run_question(db, question, "optimized", advance=_advance, cache_salt="a")
    second = evaluation.run_question(db, question, "optimized", advance=_advance, cache_salt="b")
    third = evaluation.run_question(db, question, "optimized", advance=_advance, cache_salt="b")
    assert first["llm_cache_hits"] == 0
    assert second["llm_cache_hits"] == 0  # muối khác: không dùng cache của lần trước
    assert third["llm_cache_hits"] > 0  # cùng muối: cache có hiệu lực
    assert {run.created_by for run in db.query(ResearchRun)} == {runner.EVAL_ACTOR}
    run = db.query(ResearchRun).first()
    run.status, run.next_attempt_at = "queued", None
    db.commit()
    assert runner.claim_next_research_run(db) is None


def test_entity_recall_ignores_the_question_header():
    markdown = (
        "# T\n\n> **Câu hỏi:** Gartner nói gì?\n\n## Tóm tắt\n\nNội dung. [1](https://a.example)"
        "\n\n## Nguồn\n\n1. [Gartner](https://a.example)\n"
    )
    assert "gartner" not in evaluation.report_body(markdown).casefold()
