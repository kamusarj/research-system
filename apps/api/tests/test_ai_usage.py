import httpx
import pytest
from pydantic import BaseModel, SecretStr

from app.core.observability import provider_observation
from app.models import AICallMetric
from app.services import ai, ai_usage


class Probe(BaseModel):
    answer: str


@pytest.fixture
def recorded():
    rows: list[dict] = []
    previous = ai_usage.set_recorder(rows.append)
    yield rows
    ai_usage.set_recorder(previous)


def _fake_post(payload):
    def post(url, **kwargs):
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    return post


def test_chat_completions_usage_is_recorded_without_content(monkeypatch, recorded):
    monkeypatch.setattr(ai.DeepSeekProvider, "api_key", SecretStr("test-key"))
    monkeypatch.setattr(
        ai.httpx,
        "post",
        _fake_post(
            {
                "choices": [{"message": {"content": '{"answer": "ok"}'}}],
                "usage": {
                    "prompt_tokens": 1200,
                    "completion_tokens": 80,
                    "prompt_cache_hit_tokens": 1024,
                },
            }
        ),
    )
    runtime = ai.DeepSeekProvider()
    with provider_observation(provider="deepseek", model=runtime.name, operation="probe"):
        result = runtime.complete_json("secret prompt body", Probe)

    assert result.answer == "ok"
    assert len(recorded) == 1
    row = recorded[0]
    assert row["operation"] == "probe"
    assert row["outcome"] == "success"
    assert row["input_tokens"] == 1200
    assert row["output_tokens"] == 80
    assert row["cached_input_tokens"] == 1024
    assert row["prompt_chars"] == len("secret prompt body")
    assert "secret prompt body" not in repr(row)


def test_openai_and_gemini_usage_shapes():
    assert ai_usage.usage_from_openai_responses(
        {
            "usage": {
                "input_tokens": 10,
                "output_tokens": 3,
                "input_tokens_details": {"cached_tokens": 4},
            }
        }
    ) == {"input_tokens": 10, "output_tokens": 3, "cached_input_tokens": 4}
    assert ai_usage.usage_from_gemini(
        {"usageMetadata": {"promptTokenCount": 7, "candidatesTokenCount": 2}}
    ) == {"input_tokens": 7, "output_tokens": 2, "cached_input_tokens": None}


def test_failed_call_is_recorded_as_error(recorded):
    with pytest.raises(RuntimeError):
        with provider_observation(provider="codex", model="m", operation="probe"):
            ai_usage.report_usage(input_tokens=5)
            raise RuntimeError("provider down")
    assert recorded[0]["outcome"] == "error"
    assert recorded[0]["input_tokens"] == 5


def test_usage_outside_observation_is_ignored(recorded):
    ai_usage.report_usage(input_tokens=99)
    assert recorded == []


def test_recorder_failure_never_breaks_the_call():
    def broken(_row):
        raise RuntimeError("database unavailable")

    previous = ai_usage.set_recorder(broken)
    try:
        with provider_observation(provider="codex", model="m", operation="probe"):
            ai_usage.report_usage(input_tokens=1)
    finally:
        ai_usage.set_recorder(previous)


def test_metric_row_persists(db):
    previous = ai_usage.set_recorder(lambda row: (db.add(AICallMetric(**row)), db.commit()))
    try:
        with provider_observation(provider="codex", model="gpt", operation="link-classification"):
            ai_usage.report_usage(input_tokens=300, output_tokens=40, prompt_chars=1500)
    finally:
        ai_usage.set_recorder(previous)
    stored = db.query(AICallMetric).one()
    assert (stored.operation, stored.input_tokens, stored.output_tokens) == (
        "link-classification",
        300,
        40,
    )


def test_usage_report_aggregates_by_operation(db):
    from app.services.ai_usage_report import ai_usage_report

    for tokens in (100, 300):
        db.add(
            AICallMetric(
                operation="link-classification",
                provider="codex",
                model="gpt",
                outcome="success",
                latency_ms=1000,
                input_tokens=tokens,
                output_tokens=10,
            )
        )
    db.commit()
    report = ai_usage_report(db, since_hours=1)
    [row] = report["operations"]
    assert row["calls"] == 2
    assert row["avg_input_tokens"] == 200.0
    assert row["total_output_tokens"] == 20


def test_cli_bridge_total_only_usage_is_not_recorded_as_zero(monkeypatch, recorded):
    monkeypatch.setattr(
        ai,
        "bridge_complete",
        lambda *_args, **_kwargs: {
            "output": {"answer": "ok"},
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 1234},
        },
    )
    runtime = ai.CodexProvider()
    with provider_observation(provider="codex", model=runtime.name, operation="probe"):
        runtime.complete_json("prompt", Probe)
    row = recorded[0]
    assert row["total_tokens"] == 1234
    assert row["input_tokens"] is None and row["output_tokens"] is None
