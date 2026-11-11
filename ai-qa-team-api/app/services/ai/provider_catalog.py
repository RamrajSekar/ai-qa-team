PROVIDER_CATALOG = {
    "managed": {"label": "Managed", "modes": ["MANAGED"], "fields": [
        {"name": "model", "label": "Model", "secret": False, "required": True},
    ], "capabilities": ["structured_output"]},
    "openai": {"label": "OpenAI", "modes": ["BYOK"], "fields": [
        {"name": "model", "label": "Model", "secret": False, "required": True},
        {"name": "api_key", "label": "API Key", "secret": True, "required": True},
    ], "capabilities": ["structured_output", "tool_calling", "vision", "streaming"]},
    "azure_openai": {"label": "Azure OpenAI", "modes": ["BYOK"], "fields": [
        {"name": "endpoint", "label": "Endpoint", "secret": False, "required": True},
        {"name": "deployment", "label": "Deployment", "secret": False, "required": True},
        {"name": "api_version", "label": "API Version", "secret": False, "required": True},
        {"name": "api_key", "label": "API Key", "secret": True, "required": True},
    ], "capabilities": ["structured_output", "tool_calling", "vision", "streaming"]},
}


def public_provider_catalog() -> list[dict]:
    return [{"provider_id": key, **value} for key, value in PROVIDER_CATALOG.items()]
