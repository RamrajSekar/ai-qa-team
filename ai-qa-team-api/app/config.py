from pydantic_settings import BaseSettings

class Settings(BaseSettings):
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
        extra = "ignore"

settings = Settings()
