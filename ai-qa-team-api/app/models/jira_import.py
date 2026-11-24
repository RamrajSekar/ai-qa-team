from typing import Literal
from uuid import UUID
from pydantic import Field, SecretStr
from app.models.approved_visual_run import Contract, RequestKey


class JiraRevision(Contract):
    expected_revision: int = Field(ge=0)


class JiraPreview(Contract):
    issue_keys: list[str] = Field(min_length=1, max_length=10)


class JiraSelection(Contract):
    issue_id: str = Field(pattern=r"^[0-9]{1,30}$")
    fields: list[Literal["title", "description", "acceptance_criteria"]] = Field(min_length=1, max_length=3)


class JiraApply(Contract):
    preview_id: RequestKey
    selections: list[JiraSelection] = Field(min_length=1, max_length=10)
    reviewed: Literal[True]


class JiraOAuthStart(JiraRevision):
    pass


class JiraOAuthComplete(Contract):
    state: str = Field(min_length=40, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    code: SecretStr = Field(min_length=1, max_length=4096)


class JiraOAuthGrant(Contract):
    grant_id: RequestKey
    cloud_id: UUID = Field(strict=False)


class JiraOAuthSelect(JiraOAuthGrant):
    project_key: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,19}$")
    acceptance_field: str | None = Field(default=None, pattern=r"^customfield_[0-9]{1,10}$")
