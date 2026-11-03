"""The host bridge runs subscription CLIs on content that may come from untrusted pages.

These tests pin the parts that keep that safe and predictable without spending quota: the
request contract, the sandbox shape, the output parsing for each CLI and the HTTP surface.
"""

import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest

from app import ai_cli_bridge as bridge
from app.schemas.documents import DocumentGraphExtraction
from app.schemas.ingestion import LinkClassification

TOKEN = "t" * 40
SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["label", "tags"],
    "additionalProperties": False,
}


@pytest.fixture
def config(tmp_path: Path) -> bridge.BridgeConfig:
    binaries = {}
    for name in ("claude", "codex", "agy", "bwrap", "xdg-dbus-proxy"):
        path = tmp_path / "bin" / name
        path.parent.mkdir(exist_ok=True)
        path.write_text("#!/bin/sh\n")
        path.chmod(0o755)
        binaries[name] = str(path)
    auth = tmp_path / "codex-auth.json"
    auth.write_text("{}")
    return bridge.BridgeConfig(
        token=TOKEN,
        state_dir=tmp_path / "state",
        claude_bin=binaries["claude"],
        codex_bin=binaries["codex"],
        agy_bin=binaries["agy"],
        bwrap_bin=binaries["bwrap"],
        dbus_proxy_bin=binaries["xdg-dbus-proxy"],
        codex_auth_file=auth,
    )


def request(backend: str, **overrides) -> bridge.CompletionRequest:
    values = {"backend": backend, "prompt": "Classify ReAct", "schema": SCHEMA, "system": "sys"}
    values.update(overrides)
    return bridge.CompletionRequest(**values)


def test_strict_schema_requires_every_field_and_keeps_property_names():
    schema = DocumentGraphExtraction.model_json_schema()
    strict = bridge.strict_schema(schema)

    assert strict is not None
    assert strict["required"] == list(strict["properties"])
    assert strict["additionalProperties"] is False
    node = strict["$defs"]["DocumentGraphNodeProposal"]
    assert node["required"] == list(node["properties"])
    assert {"type": "null"} in node["properties"]["parent_local_id"]["anyOf"]
    assert '"default"' not in json.dumps(strict)


def test_strict_schema_only_strips_keywords_not_property_names():
    schema = {
        "type": "object",
        "title": "Doc",
        "properties": {"title": {"type": "string", "default": "x"}, "default": {"type": "integer"}},
        "required": ["title"],
    }

    strict = bridge.strict_schema(schema)

    assert set(strict["properties"]) == {"title", "default"}
    assert "title" not in strict and "default" not in strict["properties"]["title"]
    assert strict["properties"]["default"] == {"anyOf": [{"type": "integer"}, {"type": "null"}]}


def test_strict_schema_refuses_free_form_objects():
    # `relations: list[dict[str, str]]` cannot be expressed in strict mode.
    assert bridge.strict_schema(LinkClassification.model_json_schema()) is None


def test_optional_nulls_are_dropped_so_model_defaults_apply():
    schema = DocumentGraphExtraction.model_json_schema()
    output = {"nodes": None, "edges": [], "limitations": None}

    cleaned = bridge.drop_optional_nulls(output, schema)

    assert cleaned == {"edges": []}
    assert DocumentGraphExtraction.model_validate(cleaned).nodes == []


@pytest.mark.parametrize(
    "text",
    ['{"a": 1}', '```json\n{"a": 1}\n```', 'Here you go:\n{"a": 1}\nThanks'],
)
def test_json_object_is_extracted_from_common_reply_shapes(text):
    assert bridge.extract_json_object(text) == {"a": 1}


def test_a_reply_without_json_is_an_invalid_output():
    with pytest.raises(bridge.BridgeError) as error:
        bridge.extract_json_object("I cannot help with that")
    assert error.value.code == "CLI_INVALID_OUTPUT"


@pytest.mark.parametrize(
    ("text", "code", "status"),
    [
        ("You've hit your usage limit. Try again at 5pm.", "CLI_RATE_LIMITED", 429),
        ("Error: not logged in. Please run /login", "CLI_LOGIN_FAILED", 403),
        ("segfault", "CLI_FAILED", 502),
    ],
)
def test_cli_failures_map_to_stable_codes(text, code, status):
    error = bridge.classify_failure(text)
    assert (error.code, error.status) == (code, status)


@pytest.mark.parametrize(
    "payload",
    [
        {"backend": "bash", "prompt": "x", "schema": SCHEMA},
        {"backend": "codex", "prompt": " ", "schema": SCHEMA},
        {"backend": "codex", "prompt": "x", "schema": {"type": "array"}},
        {"backend": "codex", "prompt": "x", "schema": SCHEMA, "model": "gpt; rm -rf /"},
        {"backend": "codex", "prompt": "x", "schema": SCHEMA, "effort": "extreme"},
        {"backend": "codex", "prompt": "x", "schema": SCHEMA, "timeout_seconds": 5000},
    ],
)
def test_invalid_requests_are_rejected(payload):
    with pytest.raises(bridge.BridgeError) as error:
        bridge.CompletionRequest.parse(payload, max_timeout=900)
    assert error.value.status == 400


def test_sandbox_hides_home_and_clears_the_environment(config, tmp_path):
    home, work = tmp_path / "home", tmp_path / "work"
    argv = bridge.sandbox_argv(
        ["/usr/bin/true"],
        config=config,
        home=home,
        workdir=work,
        ro_binds=[],
        rw_binds=[(config.codex_auth_file, home / ".codex/auth.json")],
        env={"HOME": str(home)},
    )

    assert argv[0] == config.bwrap_bin
    for flag in ("--unshare-all", "--share-net", "--clearenv", "--die-with-parent"):
        assert flag in argv
    bound = {argv[index + 1] for index, item in enumerate(argv) if item.endswith("bind")}
    assert str(Path.home()) not in bound
    assert str(config.codex_auth_file) in bound
    assert argv[argv.index("--tmpfs", argv.index("/tmp")) + 1] == "/run"
    assert argv[-1] == "/usr/bin/true"


def test_claude_runs_without_tools_and_without_api_keys(config, monkeypatch):
    seen = {}
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-not-leak")

    def fake_run(argv, *, stdin, env, cwd, timeout):
        seen.update(argv=argv, stdin=stdin, env=env)
        payload = {
            "is_error": False,
            "structured_output": {"label": "research", "tags": ["agents"]},
            "usage": {"input_tokens": 3, "output_tokens": 5, "cache_read_input_tokens": 7},
        }
        return bridge.RunResult(0, json.dumps(payload), "")

    monkeypatch.setattr(bridge, "run_process", fake_run)
    completion = bridge.Runner(config).complete(request("claude_code", effort="low"))

    assert completion.output == {"label": "research", "tags": ["agents"]}
    assert completion.usage == {"input_tokens": 10, "output_tokens": 5}
    argv = seen["argv"]
    assert argv[argv.index("--tools") + 1] == ""
    assert "--safe-mode" in argv and "--strict-mcp-config" in argv
    assert argv[argv.index("--model") + 1] == "sonnet"
    assert "ANTHROPIC_API_KEY" not in seen["env"]
    assert "Classify ReAct" in seen["stdin"]


def test_claude_usage_limit_is_reported_as_rate_limited(config, monkeypatch):
    def fake_run(argv, **_kwargs):
        payload = {"is_error": True, "result": "Claude usage limit reached|1761300000"}
        return bridge.RunResult(1, json.dumps(payload), "")

    monkeypatch.setattr(bridge, "run_process", fake_run)
    with pytest.raises(bridge.BridgeError) as error:
        bridge.Runner(config).complete(request("claude_code"))
    assert error.value.code == "CLI_RATE_LIMITED"


def _codex_writer(messages: list[str], seen: list[list[str]]):
    def fake_run(argv, *, stdin, env, cwd, timeout):
        seen.append(argv)
        message = messages.pop(0)
        if message.startswith("ERR:"):
            return bridge.RunResult(1, "", message.removeprefix("ERR:"))
        Path(argv[argv.index("-o") + 1]).write_text(message)
        return bridge.RunResult(0, "", "tokens used\n1,234\n")

    return fake_run


def test_codex_runs_sandboxed_with_a_strict_schema(config, monkeypatch):
    seen: list[list[str]] = []
    monkeypatch.setattr(bridge, "run_process", _codex_writer(['{"label":"x","tags":[]}'], seen))

    completion = bridge.Runner(config).complete(request("codex"))

    argv = seen[0]
    assert argv[0] == config.bwrap_bin
    assert "--output-schema" in argv
    assert argv[argv.index("--sandbox") + 1] == "read-only"
    assert "--ignore-user-config" in argv
    disabled = {argv[index + 1] for index, value in enumerate(argv) if value == "--disable"}
    assert {"shell_tool", "unified_exec", "multi_agent", "multi_agent_v2"} <= disabled
    assert completion.output == {"label": "x", "tags": []}
    assert completion.usage["total_tokens"] == 1234


def test_codex_retries_without_schema_when_strict_mode_is_rejected(config, monkeypatch):
    seen: list[list[str]] = []
    monkeypatch.setattr(
        bridge,
        "run_process",
        _codex_writer(
            ["ERR:invalid_json_schema: unsupported keyword", '{"label":"x","tags":[]}'], seen
        ),
    )

    completion = bridge.Runner(config).complete(request("codex"))

    assert "--output-schema" in seen[0]
    assert "--output-schema" not in seen[1]
    assert completion.output["label"] == "x"


def test_codex_free_form_schema_is_described_in_the_prompt(config, monkeypatch):
    prompts: list[str] = []

    def fake_run(argv, *, stdin, env, cwd, timeout):
        prompts.append(stdin)
        Path(argv[argv.index("-o") + 1]).write_text('{"a": "b"}')
        return bridge.RunResult(0, "", "")

    monkeypatch.setattr(bridge, "run_process", fake_run)
    free_form = {"type": "object", "additionalProperties": {"type": "string"}}
    bridge.Runner(config).complete(request("codex", schema=free_form))

    assert "JSON Schema" in prompts[0]


class _NoProxy:
    """Stands in for the D-Bus keyring proxy, which needs a real session bus."""

    def __init__(self, _config, directory):
        self.socket = directory / "bus"

    def __enter__(self):
        self.socket.write_text("")
        return self

    def __exit__(self, *_args):
        return None


def test_antigravity_reads_the_final_stream_event(config, monkeypatch):
    seen = {}

    def fake_run(argv, *, stdin, env, cwd, timeout):
        seen.update(argv=argv, stdin=stdin, env=env)
        events = [
            {"event": "init", "init": {"tools": ["run_command"]}},
            {
                "event": "result",
                "result": {
                    "status": "SUCCESS",
                    "structured_output": {"label": "research", "tags": []},
                    "usage": {"input_tokens": 9, "output_tokens": 2},
                },
            },
        ]
        return bridge.RunResult(0, "\n".join(json.dumps(event) for event in events), "")

    monkeypatch.setattr(bridge, "run_process", fake_run)
    monkeypatch.setattr(bridge, "DbusSecretsProxy", _NoProxy)
    completion = bridge.Runner(config).complete(request("antigravity"))

    assert completion.output == {"label": "research", "tags": []}
    assert seen["argv"][0] == config.bwrap_bin
    message = json.loads(seen["stdin"])
    assert message["event"] == "user" and "Classify ReAct" in message["message"]["content"]
    assert seen["env"]["DBUS_SESSION_BUS_ADDRESS"].startswith("unix:path=/run/user/")


def test_antigravity_error_is_classified(config, monkeypatch):
    def fake_run(argv, **_kwargs):
        event = {
            "event": "result",
            "result": {"status": "ERROR", "error": "You are not logged into Antigravity."},
        }
        return bridge.RunResult(1, json.dumps(event), "")

    monkeypatch.setattr(bridge, "run_process", fake_run)
    monkeypatch.setattr(bridge, "DbusSecretsProxy", _NoProxy)
    with pytest.raises(bridge.BridgeError) as error:
        bridge.Runner(config).complete(request("antigravity"))
    assert error.value.code == "CLI_LOGIN_FAILED"


def test_a_missing_cli_is_unavailable(config):
    Path(config.agy_bin).unlink()
    with pytest.raises(bridge.BridgeError) as error:
        bridge.Runner(config).complete(request("antigravity"))
    assert error.value.code == "CLI_UNAVAILABLE"


class FakeRunner:
    def __init__(self):
        self.requests: list[bridge.CompletionRequest] = []

    def available(self, backend: str) -> bool:
        return backend != "antigravity"

    def complete(self, completion_request):
        self.requests.append(completion_request)
        if completion_request.backend == "claude_code":
            raise bridge.BridgeError("CLI_RATE_LIMITED", 429, "limit")
        return bridge.Completion({"label": "x", "tags": []}, "gpt-6-luna", {"input_tokens": 1})


@pytest.fixture
def server(config):
    runner = FakeRunner()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), bridge.make_handler(config, runner))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", runner
    httpd.shutdown()


def test_http_requires_the_bridge_token(server):
    url, runner = server
    response = httpx.post(
        f"{url}/v1/complete", json={"backend": "codex"}, headers={"Authorization": "Bearer nope"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "CLI_BRIDGE_UNAUTHORIZED"
    assert runner.requests == []


def test_http_completes_and_reports_errors(server):
    url, runner = server
    headers = {"Authorization": f"Bearer {TOKEN}"}
    body = {"backend": "codex", "prompt": "x", "schema": SCHEMA}

    ok = httpx.post(f"{url}/v1/complete", json=body, headers=headers)
    limited = httpx.post(
        f"{url}/v1/complete", json=body | {"backend": "claude_code"}, headers=headers
    )
    bad = httpx.post(f"{url}/v1/complete", json=body | {"backend": "shell"}, headers=headers)

    assert ok.status_code == 200 and ok.json()["output"] == {"label": "x", "tags": []}
    assert limited.status_code == 429 and limited.json()["error"]["code"] == "CLI_RATE_LIMITED"
    assert bad.status_code == 400
    assert [item.backend for item in runner.requests] == ["codex", "claude_code"]


def test_http_health_lists_backends(server):
    url, _runner = server
    response = httpx.get(f"{url}/v1/health", headers={"Authorization": f"Bearer {TOKEN}"})

    backends = response.json()["backends"]
    assert backends["codex"]["available"] is True
    assert backends["antigravity"]["available"] is False
