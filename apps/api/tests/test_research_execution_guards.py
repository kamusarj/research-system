"""Ownership, verifier and CPU regressions; optionally exercise the same cases on disposable PG.

Set RESEARCH_LEASE_TEST_DATABASE_URL to an already migrated baa_ci_* PostgreSQL database.
The external fixture never creates/drops a database or infers credentials from the app settings.
"""

import json
import os
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import create_engine, func, select, update
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AIOutput, ResearchItem, ResearchRun, ResearchRunClaim, ResearchRunSource
from app.services.research_agent import evidence, runner
from app.services.research_agent.schemas import PERSPECTIVES, EntailmentBatch, ReportDraft
from app.services.research_agent.writer import (
    SourceRef,
    VerifiedClaim,
    citation_coverage,
    number_sources,
    render_markdown,
    validate_draft,
)
from tests.test_research_agent import FakeLLM, FakeSearch, fake_fetch_factory, run_to_completion


@pytest.fixture
def lease_engine(db, monkeypatch):
    monkeypatch.setattr(settings, "research_agent_enabled", True)
    monkeypatch.setattr(settings, "research_max_sources", 6)
    url = os.environ.get("RESEARCH_LEASE_TEST_DATABASE_URL")
    if not url:
        yield db.get_bind()
        return
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").startswith(
        "baa_ci_"
    ):
        pytest.fail("Lease tests require a disposable baa_ci_* PostgreSQL database")
    engine = create_engine(parsed)
    try:
        yield engine
    finally:
        engine.dispose()


def _new_run(db, *, cache_salt=None):
    return runner.create_run(
        db,
        "Synthetic governed AI agents lease audit?",
        actor=f"lease-audit-{uuid.uuid4().hex}",
        enforce_limits=False,
        # PG keeps rows across test cases. Isolate cases while a replacement worker on the
        # same run preserves its salt; otherwise a cached plan can skip the race callback.
        cache_salt=uuid.uuid4().hex if cache_salt is None else cache_salt,
    )


def _replace_and_complete(engine, run_id):
    with Session(engine) as other:
        other.execute(
            update(ResearchRun)
            .where(ResearchRun.id == run_id)
            .values(
                next_attempt_at=runner.utcnow() - timedelta(seconds=1),
            )
        )
        other.commit()
        run = runner.claim_run(other, other.get(ResearchRun, run_id))
        run = runner.advance_research_run(
            other,
            run,
            llm=FakeLLM(),
            providers=[FakeSearch()],
            fetch=fake_fetch_factory(),
        )
        run, _, _, _ = run_to_completion(other, run)
        assert run.status == "completed"
        return {
            "metrics": dict(run.metrics_json),
            "report": run.report_research_id,
            "cache_count": other.scalar(select(func.count()).select_from(AIOutput)),
        }


@pytest.mark.parametrize("late_result", ["success", "provider_error"])
def test_late_llm_result_never_overwrites_newer_completed_worker(lease_engine, late_result):
    with Session(lease_engine) as original:
        run = runner.claim_run(original, _new_run(original))
        run_id, original_token = run.id, run.lease_token
        newer = {}

        class DelayedLLM(FakeLLM):
            def complete_json(self, prompt, schema):
                newer.update(_replace_and_complete(lease_engine, run_id))
                if late_result == "provider_error":
                    raise ValueError("late invalid structured response")
                return super().complete_json(prompt, schema)

        returned = runner.advance_research_run(
            original,
            run,
            llm=DelayedLLM(),
            providers=[FakeSearch()],
            fetch=fake_fetch_factory(),
        )
        assert original_token
        assert newer, "The delayed provider must execute the replacement-worker interleaving"
        assert returned.status == "completed" and returned.stage == "done"
        assert returned.lease_token is None
        assert returned.metrics_json == newer["metrics"]
        assert returned.report_research_id == newer["report"]
        assert original.scalar(select(func.count()).select_from(AIOutput)) == newer["cache_count"]


@pytest.mark.parametrize("late_result", ["success", "retryable", "permanent", "unexpected"])
def test_finalization_and_error_paths_discard_stale_pending_report_and_cache(
    lease_engine,
    monkeypatch,
    late_result,
):
    with Session(lease_engine) as original:
        run = runner.claim_run(original, _new_run(original))
        run_id, original_token = run.id, run.lease_token
        stale_report_id = str(uuid.uuid4())
        handler = runner.STAGE_HANDLERS["planning"]
        newer = {}

        def late_handler(ctx):
            if ctx.lease_token != original_token:
                return handler(ctx)
            newer.update(_replace_and_complete(lease_engine, run_id))
            ctx.metrics.update(llm_calls=999, total_tokens=999_999)
            ctx.db.add(
                ResearchItem(
                    id=stale_report_id,
                    title="Stale synthetic draft",
                    content="Synthetic",
                    type="article",
                )
            )
            ctx.db.add(
                AIOutput(
                    task="stale-worker",
                    model_name="synthetic",
                    model_version="1",
                    prompt_version="1",
                    input_hash=stale_report_id,
                    output_json={},
                    confidence=0,
                )
            )
            if late_result == "retryable":
                raise runner.RetryableStageError("AI_RESPONSE_INVALID", "late response")
            if late_result == "permanent":
                raise runner.StageFailed("SYNTHETIC_FAILURE", "late failure")
            if late_result == "unexpected":
                raise RuntimeError("late exception before post-I/O fence")
            return "searching"

        monkeypatch.setitem(runner.STAGE_HANDLERS, "planning", late_handler)
        returned = runner.advance_research_run(
            original,
            run,
            llm=FakeLLM(),
            providers=[FakeSearch()],
            fetch=fake_fetch_factory(),
        )
        assert returned.status == "completed" and returned.stage == "done"
        assert returned.metrics_json == newer["metrics"]
        assert returned.report_research_id == newer["report"]
        assert original.get(ResearchItem, stale_report_id) is None
        assert original.scalar(select(func.count()).select_from(AIOutput)) == newer["cache_count"]


def test_stale_heartbeat_rolls_back_pending_writes_before_autoflush(lease_engine):
    with Session(lease_engine) as original:
        run = runner.claim_run(original, _new_run(original))
        context = runner.RunContext(
            db=original,
            run=run,
            llm=FakeLLM(),
            providers=[],
            fetch=fake_fetch_factory(),
            flags={},
        )
        run_id = run.id
        original.rollback()  # release the read transaction before the competing claim
        with Session(lease_engine) as newer:
            newer.execute(
                update(ResearchRun)
                .where(ResearchRun.id == run_id)
                .values(
                    next_attempt_at=runner.utcnow() - timedelta(seconds=1),
                )
            )
            newer.commit()
            replacement = runner.claim_run(newer, newer.get(ResearchRun, run_id))
            replacement_token = replacement.lease_token
        stale_id = str(uuid.uuid4())
        original.add(
            ResearchItem(
                id=stale_id, title="Stale pending draft", content="Synthetic", type="article"
            )
        )
        with pytest.raises(runner.LeaseLost):
            runner._heartbeat(context)
        assert not original.new and not original.dirty
        assert original.get(ResearchItem, stale_id) is None
        assert original.get(ResearchRun, run_id).lease_token == replacement_token


def test_cancellation_revokes_worker_before_it_can_commit(lease_engine):
    with Session(lease_engine) as original:
        run = runner.claim_run(original, _new_run(original))
        run_id = run.id
        callbacks = []

        class CancellingLLM(FakeLLM):
            def complete_json(self, prompt, schema):
                callbacks.append(schema.__name__)
                with Session(lease_engine) as owner:
                    cancelled = runner.request_cancel(owner, owner.get(ResearchRun, run_id))
                    assert cancelled.status == "cancelled" and cancelled.lease_token is None
                return super().complete_json(prompt, schema)

        result = runner.advance_research_run(original, run, llm=CancellingLLM(), providers=[])
        assert callbacks == ["ResearchPlan"]
        assert result.status == "cancelled" and result.lease_token is None
        assert result.report_research_id is None


def _verification_context(db, llm):
    # TTL/conflict tests intentionally compare the same evidence/cache identity across runs.
    run = _new_run(db, cache_salt="verification-fixture")
    text = "The governed agent requires human review before moving any customer funds."
    source = ResearchRunSource(
        run_id=run.id,
        provider="synthetic",
        perspective="technical",
        url="https://audit.example/",
        canonical_url="https://audit.example/",
        content_text=text,
    )
    db.add(source)
    db.flush()
    claim = ResearchRunClaim(
        run_id=run.id,
        source_id=source.id,
        perspective="technical",
        status="matched",
        text="The governed agent requires human review.",
        quote=text,
        matched_quote=text,
        start_offset=0,
        end_offset=len(text),
    )
    db.add(claim)
    db.commit()
    run = runner.claim_run(db, run)
    return runner.RunContext(
        db=db,
        run=run,
        llm=llm,
        providers=[],
        fetch=fake_fetch_factory(),
        flags={"entailment": True, "llm_cache": True, "parallel": False},
        salt=run.config_json["cache_salt"],
    ), claim


class JudgingLLM:
    name = "synthetic-verifier"
    version = "1"

    def __init__(self, judgements):
        self.judgements = judgements
        self.calls = []

    def complete_json(self, prompt, schema):
        self.calls.append(prompt)
        return schema.model_validate({"judgements": self.judgements})


@pytest.mark.parametrize(
    "judgements",
    [
        [
            {"claim_id": "C1", "verdict": "not_supported"},
            {"claim_id": "C1", "verdict": "supported"},
        ],
        [
            {"claim_id": "C1", "verdict": "supported"},
            {"claim_id": "C1", "verdict": "not_supported"},
        ],
        [{"claim_id": "C1", "verdict": "supported"}, {"claim_id": "C1", "verdict": "supported"}],
        [{"claim_id": "C1", "verdict": "supported"}, {"claim_id": "C999", "verdict": "supported"}],
    ],
)
def test_ambiguous_verifier_batches_never_verify_or_enter_any_cache(db, monkeypatch, judgements):
    monkeypatch.setattr(settings, "research_agent_enabled", True)
    context, claim = _verification_context(db, JudgingLLM(judgements))
    assert runner.stage_verifying(context) == "writing"
    runner._commit(context)
    assert claim.status == "flagged" and claim.reason == "no_verdict"
    assert context.metrics["claims_verified"] == 0
    assert context.metrics["invalid_entailment_batches"] == 1
    assert (
        db.scalar(
            select(func.count())
            .select_from(AIOutput)
            .where(
                AIOutput.task.in_(("research-agent.entail", "research-agent.entail-claim")),
            )
        )
        == 0
    )


def test_expired_verdict_cannot_be_resurrected_by_legacy_batch_cache(db, monkeypatch):
    monkeypatch.setattr(settings, "research_agent_enabled", True)
    first_llm = JudgingLLM([{"claim_id": "C1", "verdict": "supported"}])
    first, _ = _verification_context(db, first_llm)
    runner.stage_verifying(first)
    runner._commit(first)
    cache_identity = json.dumps([first.salt, first.run.provider_name, first.llm.version, ""])
    db.add(
        AIOutput(
            task="research-agent.entail",
            model_name=first.llm.name,
            model_version=first.llm.version,
            prompt_version=runner.PROMPT_VERSIONS["entail"],
            confidence=0,
            input_hash=runner._input_hash(
                "entail",
                first.llm.name,
                EntailmentBatch,
                first_llm.calls[0],
                cache_identity,
            ),
            output_json={"judgements": [{"claim_id": "C1", "verdict": "supported"}]},
        )
    )
    db.flush()
    db.execute(update(AIOutput).values(created_at=runner.utcnow() - timedelta(days=2)))
    db.commit()
    second_llm = JudgingLLM([{"claim_id": "C1", "verdict": "not_supported"}])
    second, claim = _verification_context(db, second_llm)
    runner.stage_verifying(second)
    runner._commit(second)
    assert len(second_llm.calls) == 1
    assert claim.status == "rejected"
    assert second.metrics.get("entailment_cache_hits", 0) == 0
    assert second.metrics.get("llm_cache_hits", 0) == 0


def test_conflicting_verdicts_for_identical_claims_with_different_aliases_fail_closed(
    db, monkeypatch
):
    monkeypatch.setattr(settings, "research_agent_enabled", True)
    context, first = _verification_context(
        db,
        JudgingLLM(
            [
                {"claim_id": "C1", "verdict": "supported"},
                {"claim_id": "C2", "verdict": "not_supported"},
            ]
        ),
    )
    second = ResearchRunClaim(
        run_id=first.run_id,
        source_id=first.source_id,
        perspective=first.perspective,
        status="matched",
        text=first.text,
        quote=first.quote,
        matched_quote=first.matched_quote,
        start_offset=first.start_offset,
        end_offset=first.end_offset,
    )
    db.add(second)
    runner._commit(context)
    runner.stage_verifying(context)
    runner._commit(context)
    assert first.status == second.status == "flagged"
    assert context.metrics["claims_verified"] == 0
    assert context.metrics["conflicting_entailment_claims"] == 2
    assert (
        db.scalar(
            select(func.count())
            .select_from(AIOutput)
            .where(
                AIOutput.task == "research-agent.entail-claim",
            )
        )
        == 0
    )


def test_report_distinguishes_omitted_verified_perspectives_from_missing_evidence():
    claims = {
        f"C{i}": VerifiedClaim(
            f"C{i}", f"S{i}", perspective, f"Verified {perspective} finding.", "Quote"
        )
        for i, perspective in enumerate(PERSPECTIVES, 1)
    }
    sources = {
        f"S{i}": SourceRef(
            f"S{i}", f"https://audit{i}.example/", "Source", "audit.example", "synthetic"
        )
        for i in range(1, 6)
    }
    draft = ReportDraft.model_validate(
        {
            "title": "T",
            "sections": [
                {
                    "perspective": "summary",
                    "sentences": [{"text": "Summary", "claim_ids": list(claims)}],
                }
            ],
        }
    )
    report = validate_draft(draft, claims)
    markdown = render_markdown(
        question="Synthetic?",
        report=report,
        claims=claims,
        sources=sources,
        numbering=number_sources(report, claims, sources),
        method={},
    )
    assert markdown.count("có nhận định đã kiểm chứng, nhưng bản nháp chưa tổng hợp") == 5
    assert "chưa tìm thấy nhận định nào đủ bằng chứng" not in markdown
    assert citation_coverage(markdown) == {"cited_sentences": 5, "uncited_sentences": 0}
    assert not set(report.sections) & set(PERSPECTIVES)  # do not inflate actual coverage
    del claims["C1"]
    draft.sections[0].sentences[0].claim_ids = list(claims)
    report = validate_draft(draft, claims)
    markdown = render_markdown(
        question="Synthetic?",
        report=report,
        claims=claims,
        sources=sources,
        numbering=number_sources(report, claims, sources),
        method={},
    )
    assert markdown.count("chưa tìm thấy nhận định nào đủ bằng chứng") == 1


def test_fuzzy_matcher_has_a_deterministic_work_budget(monkeypatch):
    matcher = evidence.SequenceMatcher
    work = 0

    def counted(_junk, quote, window, **kwargs):
        nonlocal work
        work += len(quote) * len(window)
        return matcher(_junk, quote, window, **kwargs)

    monkeypatch.setattr(evidence, "SequenceMatcher", counted)
    quote = "enterprise agents improve workflow " * 10 + "safely"
    source = "enterprise agents improve workflow " * 100
    assert evidence.match_quote(quote, source) is None
    assert 0 < work <= evidence.MAX_FUZZY_TOKEN_COMPARISONS


def test_exact_and_normalized_quotes_do_not_spend_fuzzy_budget(monkeypatch):
    monkeypatch.setattr(evidence, "MAX_FUZZY_TOKEN_COMPARISONS", 0)
    text = "Gartner said “agentic AI” will handle 15% of decisions — by 2028."
    assert evidence.match_quote("will handle 15% of decisions", text).method == "exact"
    assert (
        evidence.match_quote('"agentic AI" will HANDLE 15% of decisions -', text).method
        == "normalized"
    )
    assert (
        evidence.match_quote("enterprise agents " * 10 + "safely", "enterprise agents " * 100)
        is None
    )
