from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field


class FeatureFlags(BaseModel):
    story_management: bool = False
    scenario_generation: bool = False
    test_generation: bool = False
    recorder: bool = False
    native_execution: bool = False
    approved_visual_run_admission: bool = False
    approved_visual_run_execution: bool = False
    bug_reproduction_ui: bool = False
    repository_ui: bool = False
    jira_trigger: bool = False
    failure_diagnostics: bool = False
    self_healing: bool = False
    playwright_repo_adapter: bool = False
    selenium_repo_adapter: bool = False

    # Policy switches, not a declaration that these capabilities exist yet.
    repository_discovery: bool = True
    test_registry: bool = True
    test_data_generation: bool = True


class AIUsageSettings(BaseModel):
    bug_interpreter_credit_cost: int = Field(default=1, ge=1)
    bug_interpreter_max_input_chars: int = Field(default=20_000, ge=1)
    bug_interpreter_max_output_tokens: int = Field(default=1_200, ge=1)
    max_concurrent_requests: int = Field(default=1, ge=1)
    rate_limit_requests: int = Field(default=10, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    concurrency_ttl_seconds: int = Field(default=300, ge=1)

class Settings(BaseSettings):
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    ai_usage: AIUsageSettings = Field(default_factory=AIUsageSettings)
    mongo_uri: str
    mongo_db: str

    redis_host: str
    redis_port: int
    redis_username: str
    redis_password: str

    ai_provider: str = "openai"
    openai_api_key: str | None = None
    llm_secret_master_key: str | None = None
    app_env: str = "development"
    app_port: int = 8000
    enable_local_repositories: bool = False
    browserstack_username: str | None = None
    browserstack_access_key: str | None = None

    session_secret_key: str
    jwt_secret_key: str
    cors_origins: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None
    frontend_url: str | None = None
    platform_owner_email: str | None = None

    github_client_id: str | None = None
    github_client_secret: str | None = None
    github_redirect_uri: str | None = None
    
    gitlab_client_id: str | None = None
    gitlab_client_secret: str | None = None
    gitlab_redirect_uri: str | None = None

    bitbucket_client_id: str | None = None
    bitbucket_client_secret: str | None = None
    bitbucket_redirect_uri: str | None = None
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
        extra = "ignore"

settings = Settings()
