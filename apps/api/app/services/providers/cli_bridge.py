"""Nhà cung cấp AI dùng quota Claude Code, Codex và Antigravity qua cầu nối trên máy chủ.

Container không có CLI hay phiên đăng nhập, nên mọi lời gọi đi qua `app/ai_cli_bridge.py`
đang chạy trên máy chủ. Lỗi được trả về dưới dạng mã HTTP thông thường để các đường xử lý
lỗi sẵn có của tác vụ nền (401/403/429/timeout) vẫn áp dụng như với API trả phí.
"""

import json
import uuid
from typing import Any

import httpx
from pydantic import SecretStr

from app.core.config import settings
from app.services.ai_output_guard import reject_credentials
from app.services.object_storage import DocumentError
from app.services.providers.openai_graph_chat import GraphProviderResponse, GraphToolCall

CLI_PROVIDERS = ("claude_code", "codex", "antigravity")


def cli_model(backend: str) -> str:
    return {
        "claude_code": settings.claude_code_model,
        "codex": settings.codex_model,
        "antigravity": settings.antigravity_model,
    }[backend]


def cli_effort(backend: str) -> str | None:
    # Antigravity chọn mức suy luận qua tên model (ví dụ `-low`/`-medium`), không qua cờ riêng.
    return {"claude_code": settings.claude_code_effort, "codex": settings.codex_effort}.get(backend)


def bridge_configured() -> bool:
    token = settings.ai_cli_bridge_token
    return bool(settings.ai_cli_bridge_url.strip()) and (
        token is not None and bool(token.get_secret_value().strip())
    )


def _headers() -> dict[str, str]:
    token = settings.ai_cli_bridge_token
    if not bridge_configured() or token is None:
        raise httpx.RequestError("AI CLI bridge is not configured")
    return {"Authorization": f"Bearer {token.get_secret_value()}"}


def bridge_complete(
    backend: str,
    *,
    prompt: str,
    schema: dict[str, Any],
    system: str = "",
) -> dict[str, Any]:
    """Gửi một lượt tới CLI và trả về toàn bộ phản hồi của cầu nối (có `output` và `usage`)."""

    response = httpx.post(
        f"{settings.ai_cli_bridge_url.rstrip('/')}/v1/complete",
        headers=_headers(),
        json={
            "backend": backend,
            "model": cli_model(backend),
            "effort": cli_effort(backend),
            "system": system,
            "prompt": prompt,
            "schema": schema,
            "timeout_seconds": settings.ai_cli_timeout_seconds,
        },
        # Cầu nối có thể xếp hàng chờ lượt CLI trống trước khi chạy.
        timeout=settings.ai_cli_timeout_seconds + 60,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("output"), dict):
        raise ValueError("AI CLI bridge returned an invalid response")
    return payload


def bridge_backend_available(backend: str) -> bool:
    try:
        response = httpx.get(
            f"{settings.ai_cli_bridge_url.rstrip('/')}/v1/health",
            headers=_headers(),
            timeout=3.0,
        )
        response.raise_for_status()
        backends = response.json().get("backends", {})
        return bool(backends.get(backend, {}).get("available"))
    except (httpx.HTTPError, TypeError, ValueError, AttributeError):
        return False


def bridge_error_code(response: httpx.Response) -> str:
    try:
        error = response.json().get("error", {})
        return str(error.get("code") or "") if isinstance(error, dict) else ""
    except (ValueError, AttributeError):
        return ""


TOOL_PROTOCOL = (
    "You can call the tools listed below by returning them in `tool_calls`. Each call needs the "
    "tool `name` and `arguments_json`: a JSON object, encoded as a string, that matches the tool "
    "parameters. Tool results arrive in the next turn as TOOL RESULT entries. When you have what "
    "you need, return an empty `tool_calls` list and write the answer for the user in `reply`."
)


def _render_tools(tools: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"- {tool['name']}: {tool.get('description', '')}\n"
        f"  parameters: {json.dumps(tool.get('parameters', {}), ensure_ascii=False)}"
        for tool in tools
    )


def _render_transcript(input_items: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for item in input_items:
        role = item.get("role")
        if role == "user":
            blocks.append(f"USER:\n{item.get('content') or ''}")
        elif role == "assistant":
            calls = item.get("tool_calls") or []
            if calls:
                blocks.append(
                    "ASSISTANT called tools:\n"
                    + "\n".join(
                        f"- [{call.get('id')}] {call.get('name')} "
                        f"{json.dumps(call.get('arguments') or {}, ensure_ascii=False)}"
                        for call in calls
                    )
                )
            if item.get("content"):
                blocks.append(f"ASSISTANT:\n{item['content']}")
        elif item.get("type") == "function_call_output":
            blocks.append(f"TOOL RESULT [{item.get('call_id')}]:\n{item.get('output') or '{}'}")
    return "\n\n".join(blocks)


def _response_schema(tool_names: list[str]) -> dict[str, Any]:
    properties: dict[str, Any] = {"reply": {"type": "string"}}
    if tool_names:
        properties["tool_calls"] = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "enum": tool_names},
                    "arguments_json": {"type": "string"},
                },
                "required": ["name", "arguments_json"],
                "additionalProperties": False,
            },
        }
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _chat_error(name: str, response: httpx.Response) -> DocumentError:
    code = bridge_error_code(response)
    if code == "CLI_RATE_LIMITED" or response.status_code == 429:
        return DocumentError("CHAT_CLI_LIMIT_REACHED", f"{name} subscription limit reached", 429)
    if code == "CLI_LOGIN_FAILED":
        return DocumentError("CHAT_CLI_LOGIN_REQUIRED", f"{name} is not logged in on the host", 503)
    if code == "CLI_TIMEOUT":
        return DocumentError("CHAT_PROVIDER_TIMEOUT", f"{name} chat request timed out", 504)
    if response.status_code in {401, 503}:
        return DocumentError("CHAT_PROVIDER_UNAVAILABLE", f"{name} bridge is unavailable", 503)
    return DocumentError("CHAT_PROVIDER_FAILED", f"{name} returned an invalid chat response", 502)


class CliGraphChatProvider:
    """Trò chuyện có công cụ qua CLI: lời gọi công cụ được trả về bằng JSON có cấu trúc."""

    def __init__(
        self,
        backend: str,
        *,
        api_key: SecretStr | None = None,
        model: str | None = None,
    ):
        if api_key is not None or model is not None:
            raise DocumentError(
                "CHAT_PROVIDER_UNAVAILABLE",
                "CLI providers use the host login, not personal API keys",
                422,
            )
        self.name = backend
        self.model = cli_model(backend)

    def respond(
        self,
        *,
        input_items: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        instructions: str,
        metadata: dict[str, str],
    ) -> GraphProviderResponse:
        del metadata  # Không gửi định danh nghiệp vụ ra ngoài.
        if not bridge_configured():
            raise DocumentError("CHAT_PROVIDER_UNAVAILABLE", "AI CLI bridge is not configured", 503)
        tool_names = [tool["name"] for tool in tools]
        system = instructions
        if tools:
            system = f"{instructions}\n\n{TOOL_PROTOCOL}\n\nTools:\n{_render_tools(tools)}"
        prompt = (
            "Continue this conversation. Reply in the user's language.\n\n"
            f"{_render_transcript(input_items)}"
        )
        try:
            payload = bridge_complete(
                self.name, prompt=prompt, schema=_response_schema(tool_names), system=system
            )
        except httpx.TimeoutException as exc:
            raise DocumentError(
                "CHAT_PROVIDER_TIMEOUT", f"{self.name} chat request timed out", 504
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise _chat_error(self.name, exc.response) from None
        except httpx.RequestError as exc:
            raise DocumentError(
                "CHAT_PROVIDER_UNAVAILABLE", f"{self.name} bridge is unreachable", 503
            ) from exc
        except ValueError as exc:
            raise DocumentError(
                "CHAT_PROVIDER_FAILED", f"{self.name} returned an invalid chat response", 502
            ) from exc

        output = payload["output"]
        try:
            reject_credentials(output, provider=self.name)
        except ValueError as exc:
            raise DocumentError(
                "CHAT_PROVIDER_FAILED", f"{self.name} returned a rejected chat response", 502
            ) from exc
        tool_calls: list[GraphToolCall] = []
        for raw in output.get("tool_calls") or []:
            name = raw.get("name") if isinstance(raw, dict) else None
            if name not in tool_names:
                raise DocumentError(
                    "CHAT_TOOL_VALIDATION_FAILED", f"{self.name} called an unknown tool", 502
                )
            try:
                arguments = json.loads(raw.get("arguments_json") or "{}")
            except json.JSONDecodeError as exc:
                raise DocumentError(
                    "CHAT_TOOL_VALIDATION_FAILED",
                    f"{self.name} returned invalid tool arguments",
                    502,
                ) from exc
            if not isinstance(arguments, dict):
                raise DocumentError(
                    "CHAT_TOOL_VALIDATION_FAILED",
                    f"{self.name} returned non-object tool arguments",
                    502,
                )
            tool_calls.append(
                GraphToolCall(
                    call_id=f"cli_{uuid.uuid4().hex[:16]}", name=name, arguments=arguments
                )
            )
        text = str(output.get("reply") or "").strip()
        usage = payload.get("usage") or {}
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        return GraphProviderResponse(
            response_id=str(payload.get("request_id") or "") or None,
            text=text,
            tool_calls=tool_calls,
            output_items=[
                {
                    "role": "assistant",
                    "content": text,
                    "tool_calls": [
                        {"id": call.call_id, "name": call.name, "arguments": call.arguments}
                        for call in tool_calls
                    ],
                }
            ]
            if tool_calls
            else [],
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": int(usage.get("total_tokens") or input_tokens + output_tokens),
            },
        )
