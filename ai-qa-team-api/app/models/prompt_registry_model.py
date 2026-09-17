from typing import Literal

from pydantic import BaseModel, Field

PromptStatus = Literal["DRAFT", "ACTIVE", "INACTIVE"]


class PromptDraftCreate(BaseModel):
    base_version: int | Literal["CODE_DEFAULT_V1"] | None = None


class PromptDraftUpdate(BaseModel):
    system_prompt: str = Field(min_length=20, max_length=30000)


class PromptVersion(BaseModel):
    version: int
    system_prompt: str
    status: PromptStatus
    created_by: str
    created_at: str
    activated_at: str | None = None


class PromptDefinition(BaseModel):
    prompt_key: str
    name: str
    description: str
    output_contract: str
    active_version: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
