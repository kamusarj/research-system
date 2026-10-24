"""Request-scoped discovery/probe. No credentials, provider payloads or chat data persist."""

import json
import re

import httpx

from app.schemas.chat import (
    ChatModelsRead,
    ChatModelsRequest,
    ChatVerificationRead,
    ChatVerifyRequest,
)
from app.services.object_storage import DocumentError
from app.services.providers.chat_errors import chat_provider_error
from app.services.providers.openai_graph_chat import (
    DeepSeekGraphChatProvider,
    OpenAIGraphChatProvider,
)

MODELS_URLS = {
    "openai": "https://api.openai.com/v1/models",
    "deepseek": "https://api.deepseek.com/models",
}


def list_personal_models(request: ChatModelsRequest) -> ChatModelsRead:
    try:
        # Streaming bounds the catalogue/error body; no redirects or arbitrary hosts.
        with httpx.stream(
            "GET",
            MODELS_URLS[request.provider],
            headers={"Authorization": f"Bearer {request.personal_api_key.get_secret_value()}"},
            timeout=20,
            follow_redirects=False,
        ) as response:
            data = bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > 2_000_000:
                    raise ValueError("Model catalogue is too large")
            if not response.is_success:
                bounded = httpx.Response(response.status_code, content=bytes(data))
                raise chat_provider_error(request.provider, bounded, model_request=False)
            payload = json.loads(data)
        items = payload["data"]
        if not isinstance(items, list):
            raise ValueError("Invalid model catalogue")
        models = sorted(
            {
                item["id"]
                for item in items
                if isinstance(item, dict)
                and isinstance(item.get("id"), str)
                and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,199}", item["id"])
                and request.personal_api_key.get_secret_value() not in item["id"]
            }
        )
        if len(models) > 1000:
            raise ValueError("Too many models")
        return ChatModelsRead(provider=request.provider, models=models)
    except httpx.TimeoutException:
        raise DocumentError("CHAT_PROVIDER_TIMEOUT", "Model discovery timed out", 504) from None
    except httpx.RequestError:
        raise DocumentError("CHAT_PROVIDER_UNAVAILABLE", "Model discovery failed", 503) from None
    except (KeyError, TypeError, ValueError):
        raise DocumentError("CHAT_PROVIDER_FAILED", "Invalid model catalogue", 502) from None


def verify_personal_model(request: ChatVerifyRequest) -> ChatVerificationRead:
    provider_class = (
        OpenAIGraphChatProvider if request.provider == "openai" else DeepSeekGraphChatProvider
    )
    runtime = provider_class(
        api_key=request.personal_api_key,
        model=request.model_name,
        max_output_tokens=16,
        timeout=20,
    )
    # Exercises the same endpoint and tool parameters as real chat, without research
    # context, tool execution, retries, database writes or hidden model substitutions.
    runtime.respond(
        input_items=[{"role": "user", "content": "Reply OK."}],
        instructions="Connection check. Reply OK only; do not call tools.",
        tools=[
            {
                "type": "function",
                "name": "connection_check",
                "description": "No-op check",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            }
        ],
        metadata={},
    )
    return ChatVerificationRead(provider=request.provider, model_name=request.model_name)
