from datetime import datetime

from pydantic import BaseModel, Field


class GapPrioritize(BaseModel):
    priority: int = Field(ge=0, le=100)


class GapAssign(BaseModel):
    assigned_to: str = Field(min_length=1, max_length=200)


class GapDismiss(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class GapSnooze(BaseModel):
    until: datetime
