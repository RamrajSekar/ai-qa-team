from typing import Literal, Annotated
from urllib.parse import urlsplit

from pydantic import Field, model_validator, StringConstraints
from app.models.approved_visual_run import Contract, RequestKey


Line = Annotated[str, StringConstraints(max_length=2000)]


class BugDraft(Contract):
    title: str = Field(min_length=1, max_length=240)
    summary: str = Field(default="", max_length=4000)
    steps: list[Line] = Field(max_length=80)
    expected_result: str = Field(min_length=1, max_length=8000)
    actual_result: str = Field(min_length=1, max_length=5000)
    context: str = Field(default="", max_length=4000)
    missing_information: list[Line] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def nonblank(self):
        if not all(value.strip() for value in (self.title, self.expected_result, self.actual_result)):
            raise ValueError("Title and expected/actual results are required")
        return self


class BugAISuggestion(Contract):
    summary: str = Field(max_length=4000)
    missing_information: list[Line] = Field(max_length=20)


class BugLinkInput(Contract):
    kind: Literal["draft", "external"]
    idempotency_key: RequestKey
    reviewed: Literal[True]
    draft: BugDraft | None = None
    url: str | None = Field(default=None, max_length=2000)
    proposal_id: RequestKey | None = None

    @model_validator(mode="after")
    def check_kind(self):
        if self.kind == "draft":
            if self.draft is None or self.url is not None:
                raise ValueError("Supply a reviewed draft, without a URL")
        else:
            parsed = urlsplit(self.url or "")
            if (self.draft is not None or self.proposal_id is not None or parsed.scheme != "https"
                    or not parsed.hostname or parsed.username is not None or parsed.password is not None
                    or any(ord(c) < 33 for c in self.url or "") or "\\" in (self.url or "")):
                raise ValueError("Supply an absolute HTTPS bug URL without credentials")
        return self
