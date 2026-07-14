import hashlib
import json
import re
from typing import Any, Protocol, TypeVar

import httpx
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AIOutput, EmbeddingChunk, ResearchItem

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
    return (
        "Classify research about AI agents for business. Return JSON matching the supplied schema. "
        "Distinguish general concepts, named technologies, agent patterns, and business domains.\n"
        f"Title: {title}\nContent: {content[:30000]}"
    )


class BaseProvider:
    name = "base"
    version = "1"

    def enrich(self, title: str, content: str) -> EnrichmentResult:
        return self.complete_json(enrichment_prompt(title, content), EnrichmentResult)


class MockProvider(BaseProvider):
    name = "mock-research-provider"
    version = "2"

    def complete_json(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        clean = " ".join(prompt.split())
        words = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", prompt)
        ignored = {
            "the",
            "and",
            "for",
            "with",
            "this",
            "that",
            "from",
            "into",
            "research",
            "return",
            "json",
        }
        concepts = list(
            dict.fromkeys(word.title() for word in words if word.lower() not in ignored)
        )[:8]
        fields = schema.model_fields
        values: dict[str, Any] = {}
        if "summary" in fields:
            values["summary"] = clean[-500:][:280] or "Untitled research"
        if "concepts" in fields:
            values["concepts"] = concepts
        if "tags" in fields:
            values["tags"] = [value.lower().replace(" ", "-") for value in concepts[:5]]
        if "technologies" in fields:
            known = [
                name
                for name in ("LangGraph", "CrewAI", "AutoGen", "Ollama")
                if name.lower() in prompt.lower()
            ]
            values["technologies"] = known
        if "agent_patterns" in fields:
            values["agent_patterns"] = [
                name
                for name in ("RAG", "ReAct", "Plan-and-Execute", "Multi-Agent")
                if name.lower() in prompt.lower()
            ]
        if "business_domains" in fields:
            values["business_domains"] = [
                name
                for name in ("Customer Service", "Sales", "Operations", "Analytics")
                if name.lower() in prompt.lower()
            ]
        defaults = {
            "content_type": "article",
            "language": "vi" if re.search(r"[ăâđêôơưà-ỹ]", prompt.lower()) else "en",
            "relevance_score": 75.0,
            "confidence": 0.65,
            "reasoning": "Deterministic mock classification for local development.",
            "relations": [],
        }
        for field, value in defaults.items():
            if field in fields:
                values[field] = value
        return schema.model_validate(values)


class OllamaProvider(BaseProvider):
    name = settings.ollama_model
    version = "ollama-local"

    def complete_json(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        response = httpx.post(
            f"{settings.ollama_base_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "prompt": f"{prompt}\nJSON Schema: {json.dumps(schema.model_json_schema())}",
                "format": "json",
                "stream": False,
            },
            timeout=settings.ai_request_timeout,
        )
        response.raise_for_status()
        return schema.model_validate_json(response.json()["response"])


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
                        "content": "Return valid JSON matching the requested schema.",
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}\nJSON Schema: {schema_json}",
                    },
                ],
                "response_format": response_format,
            },
            timeout=settings.ai_request_timeout,
        )
        response.raise_for_status()
        return schema.model_validate_json(response.json()["choices"][0]["message"]["content"])


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
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseJsonSchema": schema.model_json_schema(),
                },
            },
            timeout=settings.ai_request_timeout,
        )
        response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return schema.model_validate_json(text)


PROVIDERS: dict[str, type[BaseProvider]] = {
    "mock": MockProvider,
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "deepseek": DeepSeekProvider,
    "gemini": GeminiProvider,
    "openrouter": OpenRouterProvider,
    "mistral": MistralProvider,
}


def provider(name: str | None = None) -> LLMProvider:
    provider_name = name or settings.ai_provider
    factory = PROVIDERS.get(provider_name)
    if not factory:
        raise HTTPException(422, f"Unsupported AI provider: {provider_name}")
    return factory()


def provider_status() -> list[dict[str, Any]]:
    configured = {
        "mock": True,
        "ollama": True,
        "openai": secret_configured(settings.openai_api_key),
        "deepseek": secret_configured(settings.deepseek_api_key),
        "gemini": secret_configured(settings.gemini_api_key),
        "openrouter": secret_configured(settings.openrouter_api_key),
        "mistral": secret_configured(settings.mistral_api_key),
    }
    return [
        {
            "id": provider_id,
            "configured": configured[provider_id],
            "active": provider_id == settings.ai_provider,
            "model": factory().name,
        }
        for provider_id, factory in PROVIDERS.items()
    ]


def run_enrichment(db: Session, item: ResearchItem, task: str = "enrich") -> AIOutput:
    runtime = provider()
    result = runtime.enrich(item.title, item.content)
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
        confidence=0.7 if settings.ai_provider == "mock" else 0.8,
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
