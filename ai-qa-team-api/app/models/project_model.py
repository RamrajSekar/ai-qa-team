from pydantic import BaseModel, Field
from typing import Optional, Dict

class AgentIdentities(BaseModel):
    recorder: str = "Recorder Agent"
    scenario_builder: str = "Scenario Builder"
    test_generator: str = "Test Generator"
    executor: str = "Executor Agent"

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    created_by: str
    agent_identities: AgentIdentities = Field(default_factory=AgentIdentities)

class ProjectResponse(BaseModel):
    id: Optional[str]
    project_id: str
    name: str
    agent_identities: Dict
    created_by: str
    created_at: str
