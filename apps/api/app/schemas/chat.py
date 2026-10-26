from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator

ChatScopeType = Literal["graph", "pillar", "node", "document", "change_set", "gap"]


class PersonalKeyRequest(BaseModel):
    personal_api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)

    @field_validator("personal_api_key")
    @classmethod
    def validate_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None:
            raw = value.get_secret_value()
            if not 8 <= len(raw) <= 4096 or any(not 33 <= ord(char) <= 126 for char in raw):
                raise ValueError("Personal API key format is invalid")
        return value


class ChatModelsRequest(PersonalKeyRequest):
    provider: Literal["openai", "deepseek"]
    personal_api_key: SecretStr = Field(exclude=True, repr=False)


class ChatVerifyRequest(ChatModelsRequest):
    model_name: str = Field(
        min_length=1, max_length=200, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]*$"
    )


class ChatModelsRead(BaseModel):
    provider: Literal["openai", "deepseek"]
    models: list[str]


class ChatVerificationRead(BaseModel):
    provider: Literal["openai", "deepseek"]
    model_name: str
    verified: Literal[True] = True


class ChatConnectionRequest(PersonalKeyRequest):
    provider: (
        Literal["openai", "deepseek", "claude_code", "codex", "antigravity", "chatgpt_plan"] | None
    ) = None
    credential_source: Literal["system", "personal"] = "system"
    model_name: str | None = Field(
        default=None, min_length=1, max_length=200, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]*$"
    )

    @model_validator(mode="after")
    def validate_connection(self) -> "ChatConnectionRequest":
        if self.credential_source == "personal":
            if not self.personal_api_key or not self.provider or not self.model_name:
                raise ValueError("Personal chat requires provider, model and API key")
            if self.provider not in {"openai", "deepseek"}:
                raise ValueError("Personal API keys are only supported for OpenAI and DeepSeek")
        elif self.personal_api_key is not None or self.model_name is not None:
            raise ValueError("System chat cannot override credentials or model")
        return self


class ChatSessionCreate(ChatConnectionRequest):
    title: str | None = Field(default=None, max_length=300)
    scope_type: ChatScopeType = "graph"
    scope_id: str | None = Field(default=None, max_length=36)

    @model_validator(mode="after")
    def validate_scope(self) -> "ChatSessionCreate":
        if self.scope_type == "graph" and self.scope_id is not None:
            raise ValueError("Graph scope does not accept a scope ID")
        if self.scope_type != "graph" and not self.scope_id:
            raise ValueError("This chat scope requires a scope ID")
        return self


class ChatTurnRequest(PersonalKeyRequest):
    content: str = Field(min_length=1, max_length=12_000)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Chat message cannot be blank")
        return stripped


class ChatGPTSharedImportRequest(ChatConnectionRequest):
    url: str = Field(min_length=1, max_length=2000)

    @field_validator("url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("ChatGPT shared link cannot be blank")
        return stripped


class ChatMessageRead(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    provider_response_id: str | None
    provider_request_id: str | None
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    linked_change_set_id: str | None
    usage: dict[str, Any]
    latency_ms: int | None
    error_code: str | None
    origin_type: Literal["local", "chatgpt_shared"]
    media: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


class ChatSessionRead(BaseModel):
    id: str
    title: str
    scope_type: ChatScopeType
    scope_id: str | None
    provider_name: str
    credential_source: Literal["system", "personal"] = "system"
    model_name: str
    conversation_summary: str
    status: str
    prompt_version: str
    source_type: Literal["local", "chatgpt_shared"]
    source_url: str | None
    source_snapshot_hash: str | None
    source_imported_at: datetime | None
    imported_message_count: int = Field(default=0, ge=0)
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ChatSessionList(BaseModel):
    items: list[ChatSessionRead]
    total: int = Field(ge=0)


class ChatTurnRead(BaseModel):
    session: ChatSessionRead
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead
    change_set_id: str | None = None


class ChatSummaryRequest(BaseModel):
    summary: str | None = Field(default=None, max_length=4_000)
