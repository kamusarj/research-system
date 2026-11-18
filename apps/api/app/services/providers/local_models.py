"""Bounded inference against operator-configured local model servers.

The browser never chooses an endpoint or provides a key. Both protocols use a
JSON tool envelope; only the application executor can run an allowed tool.
"""

import json
import math
import re
import time
import uuid
from typing import Any
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from app.core.config import settings
from app.services.ai_output_guard import redact_credentials
from app.services.object_storage import DocumentError
from app.services.prompts import SYSTEM_INSTRUCTIONS
from app.services.providers.cli_bridge import (
    TOOL_PROTOCOL,
    _render_tools,
    _render_transcript,
)
from app.services.providers.openai_graph_chat import GraphProviderResponse, GraphToolCall

LOCAL_PROVIDERS = frozenset({"ollama", "local_openai"})
MAX_MODELS = 200
_MODEL = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,199}\Z")


def _error(code: str, status: int = 502) -> DocumentError:
    # Never include upstream content, endpoint or credentials in an exception.
    return DocumentError(code, "Local model request could not be completed", status)


def _configuration(provider: str) -> tuple[str, str, str]:
    if provider not in LOCAL_PROVIDERS:
        raise _error("CHAT_PROVIDER_UNAVAILABLE", 422)
    base = getattr(settings, f"{provider}_base_url").strip().rstrip("/")
    model = getattr(settings, f"{provider}_model").strip()
    key = getattr(settings, f"{provider}_api_key")
    secret = key.get_secret_value().strip() if key is not None else ""
    try:
        parsed = urlsplit(base)
        valid = (
            parsed.scheme in {"http", "https"}
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
            and parsed.port != 0
            and not any(ord(char) < 33 for char in base)
            and not any(ord(char) < 32 or ord(char) > 126 for char in secret)
        )
    except ValueError:
        valid = False
    if not valid:
        raise _error("CHAT_PROVIDER_UNAVAILABLE", 503)
    return base, model, secret


def _model(value: str) -> str:
    if not isinstance(value, str) or not _MODEL.fullmatch(value):
        raise _error("CHAT_MODEL_UNAVAILABLE", 422)
    return value


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Repeated JSON property")
        result[key] = value
    return result


def _invalid_constant(_value: str) -> None:
    raise ValueError("Non-finite JSON number")


def _json(value: str | bytes) -> Any:
    return json.loads(value, object_pairs_hook=_strict_object, parse_constant=_invalid_constant)


def _status_error(status: int, *, model_request: bool) -> DocumentError:
    if status == 401:
        return _error("CHAT_API_KEY_INVALID", 422)
    if status == 403:
        return _error("CHAT_API_ACCESS_DENIED", 422)
    if status == 429:
        return _error("CHAT_PROVIDER_RATE_LIMITED", 429)
    if status == 404 and model_request:
        return _error("CHAT_MODEL_UNAVAILABLE", 422)
    if status in {400, 422} and model_request:
        return _error("CHAT_MODEL_INCOMPATIBLE", 422)
    if status >= 500 or status == 404:
        return _error("CHAT_PROVIDER_UNAVAILABLE", 503)
    return _error("CHAT_PROVIDER_FAILED")


def _request(
    provider: str,
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    base, _, secret = _configuration(provider)
    deadline_seconds = settings.ai_request_timeout if timeout is None else timeout
    if (
        not isinstance(deadline_seconds, int | float)
        or isinstance(deadline_seconds, bool)
        or not math.isfinite(deadline_seconds)
        or deadline_seconds <= 0
    ):
        raise _error("CHAT_PROVIDER_UNAVAILABLE", 503)
    deadline_seconds = min(deadline_seconds, settings.ai_request_timeout)
    maximum = settings.local_ai_max_response_bytes
    try:
        body = None if payload is None else json.dumps(payload, allow_nan=False).encode()
    except (TypeError, ValueError, RecursionError):
        raise _error("CHAT_PROVIDER_FAILED") from None
    if body is not None and len(body) > maximum:
        raise _error("CHAT_PROVIDER_REQUEST_REJECTED", 413)
    headers = {"Accept": "application/json", "Accept-Encoding": "identity"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
    deadline = time.monotonic() + deadline_seconds
    try:
        with httpx.Client(
            trust_env=False,
            follow_redirects=False,
            timeout=httpx.Timeout(deadline_seconds, connect=min(5.0, deadline_seconds)),
        ) as client:
            with client.stream(method, base + path, headers=headers, content=body) as response:
                if not 200 <= response.status_code < 300:
                    raise _status_error(response.status_code, model_request=payload is not None)
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise _error("CHAT_PROVIDER_FAILED")
                length = response.headers.get("content-length")
                if length is not None and (not length.isdecimal() or int(length) > maximum):
                    raise _error("CHAT_PROVIDER_FAILED")
                received = bytearray()
                for chunk in response.iter_bytes():
                    if time.monotonic() > deadline:
                        raise _error("CHAT_PROVIDER_TIMEOUT", 504)
                    if len(received) + len(chunk) > maximum:
                        raise _error("CHAT_PROVIDER_FAILED")
                    received.extend(chunk)
        result = _json(bytes(received))
        if not isinstance(result, dict):
            raise ValueError("Expected an object")
        return result
    except httpx.TimeoutException:
        raise _error("CHAT_PROVIDER_TIMEOUT", 504) from None
    except httpx.RequestError:
        raise _error("CHAT_PROVIDER_UNAVAILABLE", 503) from None
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise _error("CHAT_PROVIDER_FAILED") from None


def list_local_models(provider: str, *, timeout: float = 5.0) -> list[str]:
    payload = _request(
        provider, "GET", "/api/tags" if provider == "ollama" else "/models", timeout=timeout
    )
    items = payload.get("models" if provider == "ollama" else "data")
    if not isinstance(items, list):
        raise _error("CHAT_PROVIDER_FAILED")
    models: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("model") if provider == "ollama" else item.get("id")
        if isinstance(name, str) and _MODEL.fullmatch(name):
            models.add(name)
        if len(models) >= MAX_MODELS:
            break
    return sorted(models)


def _count(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _usage(provider: str, payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload if provider == "ollama" else payload.get("usage")
    raw = raw if isinstance(raw, dict) else {}
    input_tokens = _count(raw.get("prompt_eval_count" if provider == "ollama" else "prompt_tokens"))
    output_tokens = _count(raw.get("eval_count" if provider == "ollama" else "completion_tokens"))
    details = raw.get("prompt_tokens_details")
    details = details if isinstance(details, dict) else {}
    total = _count(raw.get("total_tokens"))
    if total is None and input_tokens is not None and output_tokens is not None:
        total = input_tokens + output_tokens
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_input_tokens": _count(details.get("cached_tokens")),
        "total_tokens": total,
    }


def _complete(
    provider: str,
    *,
    model: str,
    schema: dict[str, Any],
    system: str,
    prompt: str,
    max_output_tokens: int,
    timeout: float | None = None,
) -> tuple[str, dict[str, Any]]:
    _model(model)
    if (
        not isinstance(max_output_tokens, int)
        or isinstance(max_output_tokens, bool)
        or not 1 <= max_output_tokens <= 65_536
    ):
        raise _error("CHAT_PROVIDER_REQUEST_REJECTED", 422)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    payload: dict[str, Any] = {"model": model, "messages": messages, "stream": False}
    if provider == "ollama":
        path = "/api/chat"
        payload.update(
            {
                "format": schema,
                "think": False,
                "options": {"temperature": 0, "num_predict": max_output_tokens},
            }
        )
    else:
        path = "/chat/completions"
        payload.update(
            {
                "temperature": 0,
                "max_tokens": max_output_tokens,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "local_response", "strict": True, "schema": schema},
                },
            }
        )
    response = _request(provider, "POST", path, payload=payload, timeout=timeout)
    try:
        if provider == "ollama":
            if response.get("done") is False:
                raise ValueError("Incomplete response")
            message = response["message"]
        else:
            choices = response["choices"]
            if not isinstance(choices, list) or len(choices) != 1:
                raise ValueError("Invalid response choices")
            message = choices[0]["message"]
        if not isinstance(message, dict) or message.get("tool_calls") or message.get("refusal"):
            raise ValueError("Unexpected native tool or refusal")
        content = message["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Missing response content")
        # A broken upstream must not turn an authorization header into user-visible text.
        secret = _configuration(provider)[2]
        if secret and secret in content:
            raise ValueError("Credential echoed in response")
        return content, _usage(provider, response)
    except (KeyError, TypeError, ValueError, IndexError):
        raise _error("CHAT_PROVIDER_FAILED") from None


def complete_local_json(
    provider: str,
    prompt: str,
    schema: type[BaseModel],
    max_output_tokens: int,
    model: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    selected = model if model is not None else _configuration(provider)[1]
    content, usage = _complete(
        provider,
        model=selected,
        schema=schema.model_json_schema(),
        system=SYSTEM_INSTRUCTIONS,
        prompt=prompt,
        max_output_tokens=max_output_tokens,
    )
    try:
        parsed = _json(content)
        if not isinstance(parsed, dict):
            raise ValueError("Expected JSON object")
        result = schema.model_validate_json(json.dumps(parsed), strict=True).model_dump(mode="json")
        if not isinstance(result, dict):
            raise ValueError("Expected structured object")
    except (ValidationError, ValueError, TypeError, RecursionError):
        raise _error("CHAT_MODEL_INCOMPATIBLE", 422) from None
    return redact_credentials(result, provider=provider), usage


class _ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: str = Field(min_length=1, max_length=100)
    arguments_json: str


class _Envelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    reply: str
    tool_calls: list[_ToolCall] = Field(max_length=20)


class LocalGraphChatProvider:
    def __init__(
        self,
        provider: str,
        *,
        api_key: SecretStr | None = None,
        model: str | None = None,
        max_output_tokens: int | None = None,
        timeout: float | None = None,
    ):
        if api_key is not None:
            raise _error("CHAT_PROVIDER_UNAVAILABLE", 422)
        _, default_model, _ = _configuration(provider)
        self.name = provider
        self.model = _model(model if model is not None else default_model)
        self.max_output_tokens = (
            settings.chat_max_output_tokens if max_output_tokens is None else max_output_tokens
        )
        self.timeout = timeout

    def respond(
        self,
        *,
        input_items: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        instructions: str,
        metadata: dict[str, str],
    ) -> GraphProviderResponse:
        del metadata
        names = {tool["name"] for tool in tools}
        schema = _Envelope.model_json_schema()
        if names:
            schema["$defs"]["_ToolCall"]["properties"]["name"]["enum"] = sorted(names)
        else:
            schema["properties"]["tool_calls"]["maxItems"] = 0
        system = instructions
        if tools:
            system += f"\n\n{TOOL_PROTOCOL}\n\nTools:\n{_render_tools(tools)}"
        content, usage = _complete(
            self.name,
            model=self.model,
            schema=schema,
            system=system,
            prompt="Continue the conversation in the user's language.\n\n"
            + _render_transcript(input_items),
            max_output_tokens=self.max_output_tokens,
            timeout=self.timeout,
        )
        try:
            raw = _json(content)
            envelope = _Envelope.model_validate(raw)
        except (ValidationError, ValueError, TypeError, RecursionError):
            raise _error("CHAT_PROVIDER_FAILED") from None
        output = redact_credentials(envelope.model_dump(), provider=self.name)
        tool_calls: list[GraphToolCall] = []
        for call in output["tool_calls"]:
            if call["name"] not in names:
                raise _error("CHAT_TOOL_VALIDATION_FAILED")
            try:
                arguments = _json(call["arguments_json"])
                if not isinstance(arguments, dict):
                    raise ValueError("Expected tool argument object")
            except (ValueError, TypeError, RecursionError):
                raise _error("CHAT_TOOL_VALIDATION_FAILED") from None
            tool_calls.append(
                GraphToolCall(
                    call_id=f"local_{uuid.uuid4().hex[:16]}",
                    name=call["name"],
                    arguments=arguments,
                )
            )
        if not output["reply"].strip() and not tool_calls:
            raise _error("CHAT_PROVIDER_FAILED")
        return GraphProviderResponse(
            text=output["reply"].strip(),
            tool_calls=tool_calls,
            usage=usage,
            output_items=[
                {
                    "role": "assistant",
                    "content": output["reply"],
                    "tool_calls": [
                        {"id": call.call_id, "name": call.name, "arguments": call.arguments}
                        for call in tool_calls
                    ],
                }
            ]
            if tool_calls
            else [],
        )
