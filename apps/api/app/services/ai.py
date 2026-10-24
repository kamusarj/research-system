import hashlib
import json
import time
from typing import Any, Protocol, TypeVar

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AIOutput, EmbeddingChunk, ResearchItem
from app.services.ai_output_guard import redact_credentials
from app.services.ai_usage import (
    report_usage,
    usage_from_chat_completions,
    usage_from_gemini,
    usage_from_ollama,
    usage_from_openai_responses,
)
from app.services.prompts import SYSTEM_INSTRUCTIONS, Source, task_prompt
from app.services.providers.cli_bridge import (
    CLI_PROVIDERS,
    bridge_backend_available,
    bridge_complete,
    bridge_configured,
)

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class EnrichmentResult(BaseModel):
    summary: str
    concepts: list[str]
    tags: list[str]
    technologies: list[str] = []
    agent_patterns: list[str] = []
    business_domains: list[str] = []
    relations: list[dict[str, str]] = []


class LLMProvider(Protocol):
    name: str
    version: str

    def complete_json(self, prompt: str, schema: type[SchemaT]) -> SchemaT: ...

    def enrich(self, title: str, content: str) -> EnrichmentResult: ...


def enrichment_prompt(title: str, content: str) -> str:
    return task_prompt(
        "Classify this research about AI agents for business. Distinguish general concepts, named "
        "technologies, agent patterns, and business domains.",
        sources=[Source(content, attributes={"title": title})],
        max_chars_per_source=30000,
    )


class BaseProvider:
    name = "base"
    version = "1"

    def enrich(self, title: str, content: str) -> EnrichmentResult:
        return self.complete_json(enrichment_prompt(title, content), EnrichmentResult)


class OllamaProvider(BaseProvider):
    name = settings.ollama_model
    version = "ollama-local"

    def complete_json(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        schema_json = schema.model_json_schema()
        response = httpx.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "system": SYSTEM_INSTRUCTIONS,
                "prompt": f"{prompt}\nJSON Schema: {json.dumps(schema_json)}",
                "format": schema_json,
                "stream": False,
                "think": False,
                "options": {"temperature": 0},
            },
            timeout=settings.ai_request_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        report_usage(**usage_from_ollama(payload), prompt_chars=len(prompt))
        return schema.model_validate_json(payload["response"])


def secret_value(value: Any, provider_name: str) -> str:
    if value is None or not value.get_secret_value().strip():
        raise HTTPException(503, f"{provider_name} API key is not configured")
    return value.get_secret_value()


def secret_configured(value: Any) -> bool:
    return value is not None and bool(value.get_secret_value().strip())


class OpenAIProvider(BaseProvider):
    name = settings.openai_model
    version = "openai-responses-v1"

    def complete_json(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        response = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {secret_value(settings.openai_api_key, 'OpenAI')}"},
            json={
                "model": settings.openai_model,
                "store": False,
                "instructions": SYSTEM_INSTRUCTIONS,
                "max_output_tokens": settings.ai_max_output_tokens,
                "input": [{"role": "user", "content": prompt}],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": schema.__name__.lower(),
                        "strict": True,
                        "schema": schema.model_json_schema(),
                    }
                },
            },
            timeout=settings.ai_request_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        report_usage(**usage_from_openai_responses(payload), prompt_chars=len(prompt))
        text = payload.get("output_text")
        if not text:
            text = next(
                (
                    part.get("text")
                    for output in payload.get("output", [])
                    for part in output.get("content", [])
                    if part.get("type") == "output_text"
                ),
                None,
            )
        if not text:
            raise ValueError("OpenAI response did not contain output text")
        return schema.model_validate_json(text)


class ChatCompletionsProvider(BaseProvider):
    base_url: str
    api_key: Any
    model: str
    strict_schema = False

    def complete_json(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        schema_json = json.dumps(schema.model_json_schema())
        response_format: dict[str, Any] = {"type": "json_object"}
        if self.strict_schema:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__.lower(),
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            }
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {secret_value(self.api_key, self.version)}"},
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_INSTRUCTIONS,
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}\nJSON Schema: {schema_json}",
                    },
                ],
                "response_format": response_format,
                "temperature": 0,
                "max_tokens": settings.ai_max_output_tokens,
            },
            timeout=settings.ai_request_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        report_usage(**usage_from_chat_completions(payload), prompt_chars=len(prompt))
        return schema.model_validate_json(payload["choices"][0]["message"]["content"])


class DeepSeekProvider(ChatCompletionsProvider):
    name = settings.deepseek_model
    version = "deepseek-chat-completions"
    base_url = "https://api.deepseek.com"
    api_key = settings.deepseek_api_key
    model = settings.deepseek_model


class OpenRouterProvider(ChatCompletionsProvider):
    name = settings.openrouter_model
    version = "openrouter-chat-completions"
    base_url = "https://openrouter.ai/api/v1"
    api_key = settings.openrouter_api_key
    model = settings.openrouter_model
    strict_schema = True


class MistralProvider(ChatCompletionsProvider):
    name = settings.mistral_model
    version = "mistral-chat-completions"
    base_url = "https://api.mistral.ai/v1"
    api_key = settings.mistral_api_key
    model = settings.mistral_model
    strict_schema = True


class GeminiProvider(BaseProvider):
    name = settings.gemini_model
    version = "gemini-generate-content"

    def complete_json(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        key = secret_value(settings.gemini_api_key, "Gemini")
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent",
            headers={"x-goog-api-key": key},
            json={
                "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTIONS}]},
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": settings.ai_max_output_tokens,
                    "responseMimeType": "application/json",
                    "responseJsonSchema": schema.model_json_schema(),
                },
            },
            timeout=settings.ai_request_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        report_usage(**usage_from_gemini(payload), prompt_chars=len(prompt))
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        return schema.model_validate_json(text)


CLI_SYSTEM_PROMPT = SYSTEM_INSTRUCTIONS


class CliBridgeProvider(BaseProvider):
    """Dùng gói đăng nhập Claude Code/Codex/Antigravity trên máy chủ thay cho API trả phí."""

    backend: str

    def complete_json(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        payload = bridge_complete(
            self.backend,
            prompt=prompt,
            schema=schema.model_json_schema(),
            system=CLI_SYSTEM_PROMPT,
        )
        usage = payload.get("usage") or {}
        input_tokens = usage.get("input_tokens") or None
        output_tokens = usage.get("output_tokens") or None
        total = usage.get("total_tokens") or None
        if total is None and input_tokens is not None and output_tokens is not None:
            total = input_tokens + output_tokens
        # Codex chỉ báo tổng: để trống vào/ra (không rõ) thay vì ghi 0 gây hiểu nhầm.
        report_usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total,
            prompt_chars=len(prompt),
        )
        return schema.model_validate(redact_credentials(payload["output"], provider=self.backend))


class ClaudeCodeProvider(CliBridgeProvider):
    name = settings.claude_code_model
    version = "claude-code-cli-bridge"
    backend = "claude_code"


class CodexProvider(CliBridgeProvider):
    name = settings.codex_model
    version = "codex-cli-bridge"
    backend = "codex"


class AntigravityProvider(CliBridgeProvider):
    name = settings.antigravity_model
    version = "antigravity-cli-bridge"
    backend = "antigravity"


PROVIDERS: dict[str, type[BaseProvider]] = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "deepseek": DeepSeekProvider,
    "gemini": GeminiProvider,
    "openrouter": OpenRouterProvider,
    "mistral": MistralProvider,
    "claude_code": ClaudeCodeProvider,
    "codex": CodexProvider,
    "antigravity": AntigravityProvider,
}


def provider(name: str | None = None) -> LLMProvider:
    provider_name = name or settings.ai_provider
    factory = PROVIDERS.get(provider_name)
    if not factory:
        raise HTTPException(422, f"Unsupported AI provider: {provider_name}")
    return factory()


def ollama_reachable() -> bool:
    try:
        response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=0.75)
        response.raise_for_status()
        models = response.json().get("models", [])
        return any(
            item.get("name") == settings.ollama_model or item.get("model") == settings.ollama_model
            for item in models
        )
    except (httpx.HTTPError, TypeError, ValueError):
        return False


# A preflight is a network call per provider, so a result is reused for a short while.
# The window is long enough that a polling UI does not multiply requests, and short
# enough that fixing a key is visible without a restart.
_PREFLIGHT_TTL_SECONDS = 60.0
_preflight_cache: dict[str, tuple[float, bool]] = {}

# Each hosted provider's cheapest authenticated read. Reaching one of these proves the
# network path and the credential together, which is what a researcher needs to know
# before a submission fails halfway through.
_PREFLIGHT_TARGETS: dict[str, tuple[str, str]] = {
    "openai": ("https://api.openai.com/v1/models", "bearer"),
    "deepseek": ("https://api.deepseek.com/models", "bearer"),
    "mistral": ("https://api.mistral.ai/v1/models", "bearer"),
    "openrouter": ("https://openrouter.ai/api/v1/models", "bearer"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/models", "query"),
}

_PROVIDER_KEYS: dict[str, Any] = {
    "openai": lambda: settings.openai_api_key,
    "deepseek": lambda: settings.deepseek_api_key,
    "mistral": lambda: settings.mistral_api_key,
    "openrouter": lambda: settings.openrouter_api_key,
    "gemini": lambda: settings.gemini_api_key,
}


def preflight_provider(provider_id: str) -> bool | None:
    """Report whether a configured provider answers, without revealing anything about it.

    Returns ``None`` when there is nothing to test — an unconfigured provider, or one
    with no preflight target. Neither the key nor the provider's response is logged.
    """

    if provider_id == "ollama":
        return ollama_reachable()
    if provider_id in CLI_PROVIDERS:
        # Chỉ hỏi cầu nối CLI đã cài và đăng nhập chưa; không chạy lượt AI nào nên không tốn quota.
        return bridge_backend_available(provider_id) if bridge_configured() else None
    target = _PREFLIGHT_TARGETS.get(provider_id)
    secret = _PROVIDER_KEYS.get(provider_id, lambda: None)()
    if target is None or not secret_configured(secret):
        return None

    cached = _preflight_cache.get(provider_id)
    now = time.monotonic()
    if cached and now - cached[0] < _PREFLIGHT_TTL_SECONDS:
        return cached[1]

    url, style = target
    key = secret.get_secret_value()
    headers = {"Authorization": f"Bearer {key}"} if style == "bearer" else {}
    params = {"key": key} if style == "query" else None
    try:
        response = httpx.get(url, headers=headers, params=params, timeout=3.0)
        # 401/403 means the credential is wrong, which is exactly what this must surface.
        ok = response.status_code < 400
    except httpx.HTTPError:
        ok = False
    _preflight_cache[provider_id] = (now, ok)
    return ok


def reset_provider_preflight_cache() -> None:
    _preflight_cache.clear()


def provider_status(preflight: bool = False) -> list[dict[str, Any]]:
    configured = {
        "ollama": True,
        "openai": secret_configured(settings.openai_api_key),
        "deepseek": secret_configured(settings.deepseek_api_key),
        "gemini": secret_configured(settings.gemini_api_key),
        "openrouter": secret_configured(settings.openrouter_api_key),
        "mistral": secret_configured(settings.mistral_api_key),
        **{provider_id: bridge_configured() for provider_id in CLI_PROVIDERS},
    }
    reachable: dict[str, bool | None] = {provider_id: None for provider_id in PROVIDERS}
    if preflight:
        for provider_id in PROVIDERS:
            reachable[provider_id] = preflight_provider(provider_id)
    else:
        # The local bridge is cheap enough to check on every listing; hosted providers
        # are only contacted when a caller explicitly asks for a preflight.
        reachable["ollama"] = ollama_reachable()
    return [
        {
            "id": provider_id,
            "configured": configured[provider_id],
            "reachable": reachable[provider_id],
            "active": provider_id == settings.ai_provider,
            "chat_active": provider_id == settings.graph_chat_default_provider
            and provider_id in {"openai", "deepseek", *CLI_PROVIDERS},
            "model": factory().name,
        }
        for provider_id, factory in PROVIDERS.items()
    ]


class EnrichmentProviderError(HTTPException):
    """Lỗi nhà cung cấp có mã ổn định thay cho lỗi 500 chung."""

    def __init__(self, code: str, status_code: int) -> None:
        super().__init__(status_code=status_code, detail=code)
        self.code = code


def _enrichment_error(exc: Exception) -> EnrichmentProviderError | None:
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if status_code in {401, 403}:
            return EnrichmentProviderError("AI_PROVIDER_AUTH_FAILED", 502)
        if status_code == 429:
            return EnrichmentProviderError("AI_PROVIDER_RATE_LIMITED", 503)
        return EnrichmentProviderError("AI_PROVIDER_ERROR", 502)
    if isinstance(exc, httpx.TimeoutException):
        return EnrichmentProviderError("AI_PROVIDER_UNAVAILABLE", 504)
    if isinstance(exc, httpx.RequestError):
        return EnrichmentProviderError("AI_PROVIDER_UNAVAILABLE", 503)
    if isinstance(exc, ValidationError | ValueError):
        return EnrichmentProviderError("AI_RESPONSE_INVALID", 502)
    return None


def run_enrichment(db: Session, item: ResearchItem, task: str = "enrich") -> AIOutput:
    runtime = provider()
    title, content, research_id = item.title, item.content, item.id
    # Trả kết nối về pool trong lúc chờ nhà cung cấp AI (có thể tới hai phút).
    db.commit()
    try:
        result = runtime.enrich(title, content)
    except HTTPException:
        raise
    except Exception as exc:
        mapped = _enrichment_error(exc)
        if mapped is None:
            raise
        raise mapped from exc
    item = db.get(ResearchItem, research_id) or item
    output = result.model_dump()
    if task == "summarize":
        output = {"summary": result.summary}
    elif task == "extract-concepts":
        output = {
            "concepts": result.concepts,
            "tags": result.tags,
            "technologies": result.technologies,
            "agent_patterns": result.agent_patterns,
            "business_domains": result.business_domains,
        }
    elif task == "suggest-relations":
        output = {"relations": result.relations}
    input_hash = hashlib.sha256(f"{item.title}\n{item.content}".encode()).hexdigest()
    record = AIOutput(
        research_id=item.id,
        task=task,
        model_name=runtime.name,
        model_version=runtime.version,
        prompt_version="research-enrichment-v2",
        input_hash=input_hash,
        output_json=json.loads(json.dumps(output)),
        confidence=0.8,
    )
    db.add(record)
    if task == "enrich":
        db.execute(delete(EmbeddingChunk).where(EmbeddingChunk.research_id == item.id))
        chunks = [item.content[index : index + 800] for index in range(0, len(item.content), 800)]
        for index, chunk in enumerate(chunks or [item.title]):
            digest = hashlib.sha256(chunk.encode()).digest()
            db.add(
                EmbeddingChunk(
                    research_id=item.id,
                    chunk_index=index,
                    content=chunk,
                    embedding=[round(value / 255, 6) for value in digest[:16]],
                )
            )
    db.commit()
    db.refresh(record)
    return record
