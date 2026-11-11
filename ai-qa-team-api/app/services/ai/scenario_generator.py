from app.services.ai.llm_gateway import LLMGateway
from app.db.connection import db
from bson.objectid import ObjectId
from fastapi import HTTPException
import json
import re
from typing import List, Any
from app.services.ai.base_provider import LLMRequest

async def generate_scenarios_from_prompt(project_id: str, prompt: str) -> List[dict]:
    """
    Call the configured AI provider with the given prompt and parse the
    returned JSON list of scenarios.
    """
    raw = (await LLMGateway().generate(project_id, LLMRequest(prompt=prompt))).text

    # Extract JSON array from the response using a naive regex
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if not match:
        raise HTTPException(
            status_code=500,
            detail='AI did not return a JSON list'
        )

    json_payload = match.group(0)

    try:
        scenarios: Any = json.loads(json_payload)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'JSON parse error: {str(e)}'
        )

    if not isinstance(scenarios, list):
        raise HTTPException(
            status_code=500,
            detail='AI output is not a list'
        )

    return scenarios
