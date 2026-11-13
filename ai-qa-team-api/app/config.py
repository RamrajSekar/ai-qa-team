from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field, SecretStr, EmailStr


class FeatureFlags(BaseModel):
    test_design_admin_review: bool = False
    manual_test_results: bool = False
    automation_execution_ui: bool = False
    account_invitation_email: bool = False
    test_execution_ui: bool = False
    separate_ai_allowances: bool = False
    customer_accounts: bool = False
    account_subscriptions: bool = False
    story_management: bool = False
    scenario_generation: bool = False
    test_generation: bool = False
    recorder: bool = False
    native_execution: bool = False
    visual_runner_lab: bool = False
    visual_runner_batches: bool = False
    approved_visual_run_admission: bool = False
    approved_visual_run_execution: bool = False
    approved_workflow_worker: bool = False
    bug_reproduction_ui: bool = False
    repository_ui: bool = False
    reusable_workflows: bool = False
    product_knowledge: bool = False
    story_analysis: bool = False
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

class AIAllowanceSettings(BaseModel):
    free_managed: int = Field(default=25, ge=0)
    free_byok: int = Field(default=25, ge=0)
    pro_managed: int = Field(default=500, ge=0)
    pro_byok: int = Field(default=500, ge=0)
    enterprise_managed: int = Field(default=5000, ge=0)
    enterprise_byok: int = Field(default=5000, ge=0)


class PricingSettings(BaseModel):
    managed_monthly_usd: int = Field(default=499, ge=0)
    byok_monthly_usd: int = Field(default=349, ge=0)
    pilot_fixed_usd: int = Field(default=1000, ge=0)


class Settings(BaseSettings):
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    ai_allowances: AIAllowanceSettings = Field(default_factory=AIAllowanceSettings)
    pricing: PricingSettings = Field(default_factory=PricingSettings)
    ai_usage: AIUsageSettings = Field(default_factory=AIUsageSettings)
    mongo_uri: str
    mongo_db: str
    mongo_tls_ca_file: str | None = None

    redis_host: str
    redis_port: int
    redis_username: str
    redis_password: str

    ai_provider: str = "openai"
    openai_api_key: str | None = None
    llm_secret_master_key: str | None = None
    environment_secret_master_key: str | None = None
    app_env: str = "development"
    app_port: int = 8000
    enable_local_repositories: bool = False
    # Developer-owned paths only; never accepted from HTTP input.
    visual_runner_python: str | None = None
    visual_runner_chrome: str | None = None
    visual_runner_driver: str | None = None
    visual_runner_timeout_seconds: int = Field(default=90, ge=15, le=120)
    visual_batch_podman: str | None = None
    visual_batch_image: str | None = None  # Immutable local image ID, never a request field.
    visual_batch_global_slots: int = Field(default=5, ge=1, le=10)
    visual_batch_account_slots: int = Field(default=5, ge=1, le=10)
    visual_batch_project_slots: int = Field(default=5, ge=1, le=10)
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
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from_email: EmailStr | None = None

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
