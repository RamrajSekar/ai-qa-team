from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator


def contains_secret_field(value: Any) -> bool:
    if isinstance(value, dict):
        return any(any(word in str(key).lower() for word in ("key", "token", "secret", "password")) or contains_secret_field(item) for key, item in value.items())
    if isinstance(value, list):
        return any(contains_secret_field(item) for item in value)
    return False


class AIConfigurationInput(BaseModel):
    provider_id: Literal["managed", "openai", "azure_openai"]
    mode: Literal["MANAGED", "BYOK"]
    model: str | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)
    api_key: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_provider_fields(self):
        if contains_secret_field(self.configuration): raise ValueError("Secrets must be submitted through api_key")
        if self.provider_id == "managed" and self.mode != "MANAGED": raise ValueError("Managed provider requires MANAGED mode")
        if self.provider_id != "managed" and self.mode != "BYOK": raise ValueError("BYOK provider requires BYOK mode")
        if self.provider_id in ("managed", "openai") and not self.model: raise ValueError("Model is required")
        if self.provider_id == "azure_openai":
            missing = [key for key in ("endpoint", "deployment", "api_version") if not self.configuration.get(key)]
            if missing: raise ValueError(f"Missing Azure configuration: {', '.join(missing)}")
            endpoint = urlparse(str(self.configuration["endpoint"]))
            if endpoint.scheme != "https" or not endpoint.hostname or not endpoint.hostname.endswith(".openai.azure.com") or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
                raise ValueError("Azure endpoint must be an HTTPS openai.azure.com endpoint")
        return self


class AIConfigurationResponse(BaseModel):
    project_id: str
    provider_id: str
    mode: str
    model: str | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)
    status: str
    credential_configured: bool
    credential_suffix: str | None = None
    validated_at: str | None = None
    created_by: str
    updated_by: str
    created_at: str
    updated_at: str
    last_change: dict[str, str] | None = None


class ConnectionTestResponse(BaseModel):
    success: bool
    code: str
