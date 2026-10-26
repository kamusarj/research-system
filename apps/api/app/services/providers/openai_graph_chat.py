import json
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field, SecretStr

from app.core.config import settings
from app.services.object_storage import DocumentError
from app.services.providers.chat_errors import chat_provider_error


class GraphToolCall(BaseModel):
    call_id: str
    name: str
    arguments: dict[str, Any]


class GraphProviderResponse(BaseModel):
    response_id: str | None = None
    request_id: str | None = None
    text: str = ""
    tool_calls: list[GraphToolCall] = Field(default_factory=list)
    output_items: list[dict[str, Any]] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)


class GraphChatProvider(Protocol):
    name: str
    model: str

    def respond(
        self,
        *,
        input_items: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        instructions: str,
        metadata: dict[str, str],
    ) -> GraphProviderResponse: ...


class OpenAIGraphChatProvider:
    name = "openai"
    model = settings.openai_model

    def __init__(
        self,
        *,
        api_key: SecretStr | None = None,
        model: str | None = None,
        max_output_tokens: int | None = None,
        timeout: float | None = None,
    ):
        self._personal_api_key = api_key
        self.model = model or settings.openai_model
        self.max_output_tokens = max_output_tokens or settings.chat_max_output_tokens
        self.timeout = timeout or settings.ai_request_timeout

    def respond(
        self,
        *,
        input_items: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        instructions: str,
        metadata: dict[str, str],
    ) -> GraphProviderResponse:
        key = (
            self._personal_api_key
            if self._personal_api_key is not None
            else settings.openai_api_key
        )
        if key is None or not key.get_secret_value().strip():
            raise DocumentError(
                "CHAT_PROVIDER_UNAVAILABLE", "OpenAI API key is not configured", 503
            )
        try:
            response = httpx.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {key.get_secret_value()}"},
                json={
                    "model": self.model,
                    "store": False,
                    "instructions": instructions,
                    "input": input_items,
                    "tools": tools,
                    "tool_choice": "auto",
                    "parallel_tool_calls": True,
                    "max_output_tokens": self.max_output_tokens,
                    "metadata": metadata,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as exc:
            raise DocumentError(
                "CHAT_PROVIDER_TIMEOUT", "OpenAI chat request timed out", 504
            ) from exc
        except httpx.RequestError as exc:
            raise DocumentError(
                "CHAT_PROVIDER_UNAVAILABLE", "OpenAI chat provider is unreachable", 503
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise chat_provider_error(self.name, exc.response) from None
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise DocumentError(
                "CHAT_PROVIDER_FAILED", "OpenAI returned an invalid chat response", 502
            ) from exc

        if not isinstance(payload, dict):
            raise DocumentError(
                "CHAT_PROVIDER_FAILED", "OpenAI returned an invalid chat response", 502
            )
        if payload.get("error") or payload.get("status") in {"failed", "cancelled"}:
            raise chat_provider_error(self.name, response) from None
        output_items = payload.get("output")
        if not isinstance(output_items, list) or not all(
            isinstance(item, dict) for item in output_items
        ):
            raise DocumentError(
                "CHAT_PROVIDER_FAILED", "OpenAI returned an invalid chat response", 502
            )
        tool_calls: list[GraphToolCall] = []
        text_parts: list[str] = []
        for item in output_items:
            if item.get("type") == "function_call":
                try:
                    arguments = json.loads(item.get("arguments") or "{}")
                except json.JSONDecodeError as exc:
                    raise DocumentError(
                        "CHAT_TOOL_VALIDATION_FAILED",
                        "OpenAI returned invalid function arguments",
                        502,
                    ) from exc
                if not isinstance(arguments, dict):
                    raise DocumentError(
                        "CHAT_TOOL_VALIDATION_FAILED",
                        "OpenAI returned non-object function arguments",
                        502,
                    )
                tool_calls.append(
                    GraphToolCall(
                        call_id=str(item.get("call_id") or item.get("id") or ""),
                        name=str(item.get("name") or ""),
                        arguments=arguments,
                    )
                )
            if item.get("type") == "message":
                for part in item.get("content") or []:
                    if part.get("type") == "output_text" and part.get("text"):
                        text_parts.append(str(part["text"]))
        return GraphProviderResponse(
            response_id=payload.get("id"),
            request_id=response.headers.get("x-request-id"),
            text="\n".join(text_parts).strip(),
            tool_calls=tool_calls,
            output_items=output_items,
            usage=payload.get("usage") or {},
        )


class DeepSeekGraphChatProvider:
    name = "deepseek"
    model = settings.deepseek_model

    def __init__(
        self,
        *,
        api_key: SecretStr | None = None,
        model: str | None = None,
        max_output_tokens: int | None = None,
        timeout: float | None = None,
    ):
        self._personal_api_key = api_key
        self.model = model or settings.deepseek_model
        self.max_output_tokens = max_output_tokens or settings.chat_max_output_tokens
        self.timeout = timeout or settings.ai_request_timeout

    @staticmethod
    def _messages(input_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for item in input_items:
            role = item.get("role")
            if role in {"user", "assistant"}:
                message: dict[str, Any] = {
                    "role": role,
                    "content": item.get("content") or "",
                }
                if role == "assistant" and item.get("tool_calls"):
                    message["tool_calls"] = item["tool_calls"]
                messages.append(message)
            elif item.get("type") == "function_call_output":
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": str(item.get("call_id") or ""),
                        "content": str(item.get("output") or "{}"),
                    }
                )
        return messages

    @staticmethod
    def _tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {"type": "object"}),
                },
            }
            for tool in tools
        ]

    def respond(
        self,
        *,
        input_items: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        instructions: str,
        metadata: dict[str, str],
    ) -> GraphProviderResponse:
        del metadata  # Provider metadata stays local; no business identifiers are sent upstream.
        key = (
            self._personal_api_key
            if self._personal_api_key is not None
            else settings.deepseek_api_key
        )
        if key is None or not key.get_secret_value().strip():
            raise DocumentError(
                "CHAT_PROVIDER_UNAVAILABLE", "DeepSeek API key is not configured", 503
            )
        messages = [{"role": "system", "content": instructions}]
        messages.extend(self._messages(input_items))
        request_payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "thinking": {"type": "disabled"},
            "max_tokens": self.max_output_tokens,
        }
        if tools:
            request_payload.update(
                {
                    "tools": self._tools(tools),
                    "tool_choice": "auto",
                }
            )
        try:
            response = httpx.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {key.get_secret_value()}"},
                json=request_payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as exc:
            raise DocumentError(
                "CHAT_PROVIDER_TIMEOUT", "DeepSeek chat request timed out", 504
            ) from exc
        except httpx.RequestError as exc:
            raise DocumentError(
                "CHAT_PROVIDER_UNAVAILABLE", "DeepSeek chat provider is unreachable", 503
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise chat_provider_error(self.name, exc.response) from None
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise DocumentError(
                "CHAT_PROVIDER_FAILED", "DeepSeek returned an invalid chat response", 502
            ) from exc

        try:
            choice = payload["choices"][0]
            message = choice["message"]
            raw_tool_calls = message.get("tool_calls") or []
            if not isinstance(raw_tool_calls, list):
                raise TypeError("tool_calls must be a list")
            tool_calls: list[GraphToolCall] = []
            for item in raw_tool_calls:
                function = item["function"]
                arguments = json.loads(function.get("arguments") or "{}")
                if not isinstance(arguments, dict):
                    raise TypeError("tool arguments must be an object")
                tool_calls.append(
                    GraphToolCall(
                        call_id=str(item.get("id") or ""),
                        name=str(function.get("name") or ""),
                        arguments=arguments,
                    )
                )
            assistant_item = {
                "role": "assistant",
                "content": message.get("content") or "",
                "tool_calls": raw_tool_calls,
            }
            usage = payload.get("usage") or {}
            normalized_usage = {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise DocumentError(
                "CHAT_PROVIDER_FAILED", "DeepSeek returned an invalid chat response", 502
            ) from exc
        return GraphProviderResponse(
            response_id=str(payload.get("id") or "") or None,
            request_id=response.headers.get("x-request-id"),
            text=str(message.get("content") or "").strip(),
            tool_calls=tool_calls,
            output_items=[assistant_item] if tool_calls else [],
            usage=normalized_usage,
        )


def graph_chat_provider(
    name: str, *, api_key: SecretStr | None = None, model: str | None = None
) -> GraphChatProvider:
    # Nhập muộn vì nhà cung cấp CLI dùng lại các kiểu phản hồi khai báo trong module này.
    from app.services.providers.cli_bridge import CLI_PROVIDERS, CliGraphChatProvider

    if name in CLI_PROVIDERS:
        return CliGraphChatProvider(name, api_key=api_key, model=model)
    if name == "chatgpt_plan":
        from app.services.providers.chatgpt_plan_chat import PlanGraphChatProvider

        return PlanGraphChatProvider(api_key=api_key, model=model)
    providers: dict[str, type[OpenAIGraphChatProvider | DeepSeekGraphChatProvider]] = {
        "openai": OpenAIGraphChatProvider,
        "deepseek": DeepSeekGraphChatProvider,
    }
    provider = providers.get(name)
    if provider is None:
        raise DocumentError(
            "CHAT_PROVIDER_UNAVAILABLE",
            f"Graph chat provider '{name}' is not implemented",
            503,
        )
    return provider(api_key=api_key, model=model)
