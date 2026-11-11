from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any


class TestStep(BaseModel):
    step_id: Optional[str] = None
    # Human-readable step description for UI
    description: Optional[str] = None

    # Structured execution fields (required by StepEngine)
    action: Literal[
        "navigate",
        "click",
        "fill",       # from StepMapper
        "type",
        "assert",
        "assert_text",
        "wait_for",
        "custom",
        "unknown"
    ]

    locator: Optional[str] = None
    value: Optional[str] = None
    expected: Optional[str] = None
    url: Optional[str] = None

    # Internal metadata for recorder / mapping
    category: Optional[str] = None


# ==========================================================
# MAIN STORED MODEL IN DATABASE
# ==========================================================
class TestCase(BaseModel):
    testcase_id: str
    project_id: str
    scenario_id: str

    title: str
    description: Optional[str] = None

    # Dual representation
    steps: List[TestStep]                        # Structured automation steps
    natural_steps: Optional[List[Dict]] = None   # Raw NL steps from scenario / AI

    complexity: Optional[str] = "basic"          # basic | medium | advanced

    status: str                                  # generated | ready | disabled
    code: str                                    # Playwright code

    created_by: str
    created_at: str
    updated_by: Optional[str] = None
    updated_at: Optional[str] = None


class TestCaseCreate(BaseModel):
    testcase_id: Optional[str] = None
    story_id: Optional[str] = None
    scenario_id: Optional[str] = None
    project_id: str

    title: str
    description: Optional[str] = None

    # Natural language / recorder steps
    natural_steps: List[Dict[str, Any]] = []
    # Structured steps (what StepEngine will actually run)
    steps: List[TestStep] = []

    complexity: Optional[str] = "basic"

    # ✅ Reusable data
    data_set_id: Optional[str] = None
    data_overrides: Dict[str, Any] = Field(default_factory=dict)

    created_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_by: Optional[str] = None
    updated_at: Optional[str] = None


class TestCaseResponse(BaseModel):
    testcase_id: Optional[str]
    scenario_id: Optional[str]
    project_id: Optional[str]

    spec_kind: Optional[str] = None
    purpose: Optional[str] = None
    role: Optional[str] = None
    preconditions: List[str] = Field(default_factory=list)
    public_data: Dict[str, str] = Field(default_factory=dict)
    assertions: List[str] = Field(default_factory=list)
    cleanup: List[str] = Field(default_factory=list)
    acceptance_criteria_refs: List[str] = Field(default_factory=list)
    rule_references: List[str] = Field(default_factory=list)
    knowledge_version_id: Optional[str] = None
    story_analysis_id: Optional[str] = None

    title: str
    description: Optional[str]
    complexity: Optional[str] = None

    steps: List[TestStep]
    natural_steps: Optional[List[Dict]] = None

    status: str
    code: str

    created_by: Optional[str]
    created_at: Optional[str]
    updated_by: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        populate_by_name = True
        from_attributes = True
