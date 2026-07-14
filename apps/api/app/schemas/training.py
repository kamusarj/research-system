from typing import Any, Literal

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=80)
    source: str = Field(min_length=1, max_length=120)
    payload: dict[str, Any]
    provenance: dict[str, Any]


class ExampleUpdate(BaseModel):
    instruction: str | None = None
    context: dict[str, Any] | None = None
    expected_response: str | None = None
    split: Literal["train", "validation", "holdout"] | None = None
    pii_status: Literal["unchecked", "clear", "anonymized", "blocked"] | None = None
    policy_status: Literal["unchecked", "approved", "blocked"] | None = None
    provenance: dict[str, Any] | None = None


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=50)
    description: str | None = None


class DatasetBuild(BaseModel):
    example_ids: list[str] | None = None
