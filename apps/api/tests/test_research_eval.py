import copy
import json

import pytest

from app.evaluation import research_agent as evaluation
from app.models import ResearchRunClaim, ResearchRunSource
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
    text = "Agents " + " ".join(f"word{index}" for index in range(200))
    sources = [
        ResearchRunSource(citation_index=1, content_text=text),
        ResearchRunSource(citation_index=2, content_text=text + " updated"),
        ResearchRunSource(citation_index=3, content_text="other " * 200),
    ]
    assert evaluation.cited_duplicate_rate(sources) == round(1 / 3, 3)


def test_eval_distinguishes_missing_evidence_from_missing_report_sections(db, monkeypatch):
    monkeypatch.setattr(evaluation.settings, "research_agent_enabled", True)
    question = evaluation.load_questions(only={"q1-market-size"})[0]
    run = runner.create_run(db, question["question"], actor=runner.EVAL_ACTOR)
    run.metrics_json = {"perspectives_covered": ["market", "market", "summary"]}
    source = ResearchRunSource(
        run_id=run.id,
        provider="fixture",
        perspective="market",
        url="https://example.com/report",
        canonical_url="https://example.com/report",
    )
    db.add(source)
    db.flush()
    for perspective, status in (
        ("market", "verified"),
        ("technical", "verified"),
        ("technical", "verified"),
        ("risk_compliance", "flagged"),
    ):
        db.add(
            ResearchRunClaim(
                run_id=run.id,
                source_id=source.id,
                perspective=perspective,
                text="Synthetic finding.",
                quote="Synthetic quote from the selected source.",
                status=status,
            )
        )
    db.flush()

    result = evaluation.score_run(db, run, question, elapsed_seconds=0)

    assert result["perspectives_covered"] == ["market"]
    assert result["perspectives_with_verified_claims"] == ["market", "technical"]
    assert result["perspective_coverage"] == 0.2


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


def _row(qid="q1", *, status="completed", tokens=100):
    return {
        **dict.fromkeys(evaluation.SUMMARY_FIELDS, 1),
        "id": qid,
        "provider": "provider",
        "model": "model",
        "status": status,
        "total_tokens": tokens,
        "input_tokens": tokens,
        "output_tokens": 0,
        "llm_calls": 1,
        "usage_complete_calls": 1,
        "usage_missing_calls": 0,
        "source_snapshot_sha256": "frozen-source",
    }


def _artifact(variant="reference"):
    return {
        "variant": variant,
        "results": [_row()],
        "manifest": {
            "version": evaluation.MANIFEST_VERSION,
            "questions_sha256": "full-questions",
            "selected_questions_sha256": "selected-questions",
            "question_ids": ["q1"],
            "full_question_ids": ["q1"],
            "config": {"research_entailment_enabled": True},
            "code": {"source_sha256": "code"},
            "prompt_versions": {"write": "v2"},
            "provider_models": [["provider", "model"]],
            "variant_flags": dict(runner.VARIANTS[variant]),
            "cache_policy": "cold-per-evaluation",
            "quality_gates": evaluation.QUALITY_GATES,
            "corpus": {"mode": "frozen", "sha256": "a" * 64},
        },
    }


def test_summary_includes_failed_and_cancelled_costs():
    rows = [
        _row(),
        _row("q2", status="failed", tokens=10_000),
        _row("q3", status="cancelled", tokens=500),
    ]
    summary = evaluation.summarize(rows)
    assert summary["total_tokens"] == 10_600
    assert summary["llm_calls"] == 3
    assert summary["completion_rate"] == 0.333
    assert summary["citation_coverage"] == 1
    assert summary["cost_basis"] == "all_attempted_runs"


@pytest.mark.parametrize(
    "change",
    [
        "missing_question",
        "failed",
        "missing_manifest",
        "model",
        "effort",
        "source",
        "missing_usage",
        "weak_quality",
        "weaker_verifier",
        "warm_cache",
        "duplicates",
        "same_variant",
        "wrong_flags",
        "live_corpus",
        "unchecked_corpus",
        "malformed_corpus",
    ],
)
def test_comparison_refuses_incomplete_or_unmatched_kpi_evidence(change):
    before = _artifact()
    after = _artifact("optimized")
    if change == "missing_question":
        after["results"] = []
    elif change == "failed":
        after["results"][0].update(status="failed", total_tokens=10_000)
    elif change == "missing_manifest":
        after.pop("manifest")
    elif change == "model":
        after["manifest"]["provider_models"] = [["provider", "different-model"]]
    elif change == "effort":
        after["manifest"]["config"]["codex_effort"] = "high"
    elif change == "source":
        after["results"][0]["source_snapshot_sha256"] = "changed-source"
    elif change == "missing_usage":
        after["results"][0].update(usage_complete_calls=0, usage_missing_calls=1)
    elif change == "weak_quality":
        after["results"][0]["perspective_coverage"] = 0
    elif change == "weaker_verifier":
        before["manifest"]["variant_flags"]["entailment"] = False
    elif change == "warm_cache":
        after["manifest"]["cache_policy"] = "warm"
    elif change == "duplicates":
        after["results"].append(copy.deepcopy(after["results"][0]))
    elif change == "same_variant":
        after["variant"] = "reference"
    elif change == "wrong_flags":
        after["manifest"]["variant_flags"] = dict(runner.VARIANTS["reference"])
    elif change in {"live_corpus", "unchecked_corpus", "malformed_corpus"}:
        corpus = {
            "live_corpus": {"mode": "live"},
            "unchecked_corpus": {"mode": "frozen"},
            "malformed_corpus": {"mode": "frozen", "sha256": "invalid"},
        }[change]
        for artifact in (before, after):
            artifact["manifest"]["corpus"] = corpus
    assert evaluation.comparison_issues(before, after)
    table = evaluation.compare_markdown(before, after)
    assert "Chưa đủ điều kiện kết luận KPI" in table
    assert "%" not in table
    if change == "failed":
        assert "| total_tokens | 100 | 10000 |  |" in table


def test_comparison_allows_paired_cold_same_quality_evidence():
    before = _artifact()
    after = _artifact("optimized")
    after["results"][0]["total_tokens"] = 75
    assert evaluation.comparison_issues(before, after) == []
    assert "| total_tokens | 100 | 75 | -25% |" in evaluation.compare_markdown(before, after)


def test_run_eval_exports_reproducible_manifest_without_secrets_and_restores_flag(
    db,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(evaluation.settings, "research_agent_enabled", False)
    monkeypatch.setattr(evaluation.settings, "codex_effort", "low")
    monkeypatch.setattr(
        evaluation,
        "run_question",
        lambda *_args, **_kwargs: {
            **_row("q1-market-size"),
            "provider": "codex",
            "model": "synthetic-model",
        },
    )
    result = evaluation.run_eval(db, variant="reference", only={"q1-market-size"})
    manifest = result["manifest"]
    assert manifest["version"] == evaluation.MANIFEST_VERSION
    assert manifest["config"]["codex_effort"] == "low"
    assert manifest["question_ids"] == ["q1-market-size"]
    assert len(manifest["questions_sha256"]) == 64
    assert len(manifest["code"]["source_sha256"]) == 64
    assert manifest["provider_models"] == [("codex", "synthetic-model")]
    assert "api_key" not in json.dumps(manifest)
    assert not {"ai_cli_bridge_token", "mistral_api_key", "openai_api_key"} & set(
        manifest["config"]
    )
    assert evaluation.settings.research_agent_enabled is False


def test_kpi_comparison_rejects_models_swapped_between_questions():
    before = _artifact()
    before["results"] = [_row("q1"), {**_row("q2"), "model": "other-model"}]
    before["manifest"].update(
        question_ids=["q1", "q2"],
        full_question_ids=["q1", "q2"],
        provider_models=[["provider", "model"], ["provider", "other-model"]],
    )
    after = copy.deepcopy(before)
    after.update(variant="optimized")
    after["manifest"]["variant_flags"] = dict(runner.VARIANTS["optimized"])
    after["results"][0]["model"] = "other-model"
    after["results"][1]["model"] = "model"
    assert any("provider/model" in issue for issue in evaluation.comparison_issues(before, after))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.5, 2.0, None, "1", True])
def test_kpi_comparison_requires_finite_quality_metrics(value):
    before = _artifact()
    after = _artifact("optimized")
    after["results"][0]["citation_coverage"] = value
    assert evaluation.comparison_issues(before, after)


def test_run_eval_restores_feature_flag_on_provider_failure(db, monkeypatch):
    monkeypatch.setattr(evaluation.settings, "research_agent_enabled", False)

    def fail(*args, **kwargs):
        raise ValueError("provider failed")

    monkeypatch.setattr(evaluation, "run_question", fail)
    with pytest.raises(ValueError, match="provider failed"):
        evaluation.run_eval(db, variant="reference", only={"q1-market-size"})
    assert evaluation.settings.research_agent_enabled is False


@pytest.mark.parametrize("stop_on_provider_error", [False, True])
def test_eval_can_stop_on_provider_failure_and_keep_attempted_cost(
    db, monkeypatch, stop_on_provider_error
):
    monkeypatch.setattr(evaluation.settings, "research_agent_enabled", False)
    first, second = evaluation.load_questions()[:2]

    def run_question(_db, question, _variant, **_kwargs):
        result = _row(question["id"], tokens=125)
        if question["id"] == first["id"]:
            result.update(status="failed", error_code="AI_PROVIDER_RATE_LIMITED")
        return result

    monkeypatch.setattr(evaluation, "run_question", run_question)
    result = evaluation.run_eval(
        db,
        variant="reference",
        only={first["id"], second["id"]},
        stop_on_provider_error=stop_on_provider_error,
    )

    expected_ids = [first["id"]] if stop_on_provider_error else [first["id"], second["id"]]
    assert [row["id"] for row in result["results"]] == expected_ids
    assert result["manifest"]["question_ids"] == [first["id"], second["id"]]
    assert result["summary"]["total_tokens"] == 125 * len(expected_ids)
    assert evaluation.settings.research_agent_enabled is False
    if stop_on_provider_error:
        assert result["stopped"] == {
            "question_id": first["id"],
            "error_code": "AI_PROVIDER_RATE_LIMITED",
        }
    else:
        assert "stopped" not in result


def test_capture_existing_public_eval_sources_and_replay_without_network(db, monkeypatch, tmp_path):
    from app.models import ResearchRunSource

    monkeypatch.setattr(evaluation.settings, "research_agent_enabled", True)
    question = evaluation.load_questions(only={"q1-market-size"})[0]
    scored = evaluation.run_question(db, question, "reference", advance=_advance)
    assert scored["status"] == "completed"
    db.add(
        ResearchRunSource(
            run_id=scored["run_id"],
            provider="internal_kb",
            perspective="market",
            url="http://private.example/secret",
            canonical_url="http://private.example/secret",
            title="Private",
            content_text="Private KB text must never enter the public corpus",
        )
    )
    db.commit()
    snapshot = tmp_path / "corpus.json"
    corpus = evaluation.write_corpus_from_runs(db, snapshot, {question["id"]: scored["run_id"]})
    assert snapshot.stat().st_mode & 0o777 == 0o600
    assert "Private KB" not in snapshot.read_text()
    assert corpus["sha256"] == evaluation._digest(corpus["questions"])
    assert evaluation._load_corpus(snapshot, [question]) == corpus
    with pytest.raises(FileExistsError):
        evaluation.write_corpus_from_runs(db, snapshot, {question["id"]: scored["run_id"]})

    monkeypatch.setattr(runner, "provider", lambda *_args, **_kwargs: FakeLLM())

    def no_network(*args, **kwargs):
        raise AssertionError("Frozen replay attempted network access")

    monkeypatch.setattr(runner, "providers_from_settings", no_network)
    monkeypatch.setattr(runner, "default_fetch", no_network)
    result = evaluation.run_eval(db, variant="optimized", only={question["id"]}, corpus=snapshot)
    assert result["results"][0]["status"] == "completed"
    assert result["manifest"]["corpus"] == {"mode": "frozen", "sha256": corpus["sha256"]}
    assert (
        result["results"][0]["source_snapshot_sha256"]
        == evaluation.FrozenCorpus(corpus["questions"][question["id"]]["sources"]).snapshot_sha256
    )
    assert result["results"][0]["selected_sources_sha256"]


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/source",
        "http://localhost/x",
        "http://127.0.0.1/x",
        "http://10.0.0.1/x",
        "https://user:password@public.example/x",
        "http://[::1]/x",
        "javascript:alert(1)",
    ],
)
def test_frozen_corpus_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        evaluation.FrozenCorpus([{"url": url, "title": "T", "text": "public source"}])


def test_frozen_corpus_requires_bounded_sources_and_never_falls_back_to_fetch():
    source = {"url": "https://public.example/x", "title": "AI agents", "text": "AI agents source"}
    pool = evaluation.FrozenCorpus([source])
    assert pool.search("AI agents", limit=1)[0].url == source["url"]
    assert pool.fetch(source["url"]).text == source["text"]
    with pytest.raises(ValueError):
        pool.fetch("https://not-in-corpus.example/x")
    for sources in (
        [],
        [source, source],
        [{**source, "text": "x" * 60_001}],
        [{**source, "arbitrary": "extra"}],
    ):
        with pytest.raises(ValueError):
            evaluation.FrozenCorpus(sources)


def test_eval_rejects_corpus_capture_conflict_and_bad_snapshot_without_changing_flag(
    db,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(evaluation.settings, "research_agent_enabled", False)
    path = tmp_path / "bad.json"
    with pytest.raises(ValueError):
        evaluation.run_eval(db, variant="reference", corpus=path, capture_corpus=path)
    assert evaluation.settings.research_agent_enabled is False
    path.write_text(
        json.dumps({"version": evaluation.CORPUS_VERSION, "questions": {}, "sha256": "x"})
    )
    with pytest.raises(ValueError, match="checksum"):
        evaluation.run_eval(db, variant="reference", corpus=path)
    assert evaluation.settings.research_agent_enabled is False


def test_corpus_export_root_supports_packaged_container_layout(monkeypatch):
    from pathlib import Path

    assert (evaluation._repository_root() / "AGENTS.md").is_file()
    monkeypatch.setattr(evaluation, "__file__", "/app/app/evaluation/research_agent.py")
    assert evaluation._repository_root() == Path("/app")
