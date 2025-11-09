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

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
