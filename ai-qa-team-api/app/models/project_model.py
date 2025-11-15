from pydantic import BaseModel, Field
from typing import Optional, Dict

class AgentIdentities(BaseModel):
    recorder: str = "Recorder Agent"
    scenario_builder: str = "Scenario Builder"
    test_generator: str = "Test Generator"
    executor: str = "Executor Agent"

class Project(BaseModel):
    id: Optional[str]
    name: str
    description: Optional[str] = None
    created_by: str
    agent_identities: AgentIdentities = Field(default_factory=AgentIdentities)
