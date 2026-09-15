from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field


class FeatureFlags(BaseModel):
    story_management: bool = False
    scenario_generation: bool = False
    test_generation: bool = False
    recorder: bool = False
    native_execution: bool = False
    jira_trigger: bool = False
    failure_diagnostics: bool = False
    self_healing: bool = False
    playwright_repo_adapter: bool = False
    selenium_repo_adapter: bool = False

    # Policy switches, not a declaration that these capabilities exist yet.
    repository_discovery: bool = True
    test_registry: bool = True
    test_data_generation: bool = True

class Settings(BaseSettings):
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    mongo_uri: str
    mongo_db: str

    redis_host: str
    redis_port: int
    redis_username: str
    redis_password: str

    ai_provider: str = "openai"
    openai_api_key: str | None = None
    app_env: str = "development"
    app_port: int = 8000

    session_secret_key: str
    jwt_secret_key: str
    cors_origins: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None
    frontend_url: str | None = None

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
