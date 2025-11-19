from app.services.ai.provider_factory import get_ai_provider
from app.db.connection import db
from bson.objectid import ObjectId
from fastapi import HTTPException
import json
import re


async def generate_scenarios_from_story(prompt: str):
    provider = get_ai_provider()
    raw = await provider.generate(prompt)

    print("🔥 RAW AI OUTPUT 🔥", raw)

    # Extract JSON array
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        raise HTTPException(500, "AI did not return a JSON list")

    try:
        scenarios = json.loads(match.group(0))
    except Exception:
        raise HTTPException(500, "Invalid JSON in AI response")

    if not isinstance(scenarios, list):
        raise HTTPException(500, "AI output is not a list")

    return scenarios