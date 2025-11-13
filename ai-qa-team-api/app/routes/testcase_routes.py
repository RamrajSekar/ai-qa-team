from fastapi import APIRouter, HTTPException, Depends
from app.db.connection import db
from app.routes.auth_routes import get_current_user
from app.services.story_service import get_next_sequence
from app.ai.prompts import generate_testcase_prompt
from app.models.test_case_model import TestCaseCreate, TestCaseResponse
from app.config import settings
from openai import AsyncOpenAI
import json
from datetime import datetime, timezone

router = APIRouter(prefix="/testcases", tags=["Test Cases"])

client = AsyncOpenAI(api_key=settings.openai_api_key)

# Purpose (MVP):
# Converts scenario → JSON test structure
# No Playwright code generation
# Used by AI Test Generator Agent
@router.post("/generate")
async def generate_testcases(scenario_id: str, current_user=Depends(get_current_user)):
    """
    Generates structured testcases from scenario text using AI
    """

    # 1. Fetch scenario
    scenario = await db["scenarios"].find_one({"scenario_id": scenario_id})
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    scenario_text = f"Title: {scenario.get('title')}\nDescription: {scenario.get('description')}"

    # 2. Prepare the prompt
    prompt = generate_testcase_prompt.format(scenario_text=scenario_text)

    # 3. Call AI
    try:
        completion = await client.responses.create(
            model="gpt-4.1",
            input=prompt
        )
        raw_json = completion.output_text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {e}")

    # 4. Validate JSON output
    try:
        steps_json = json.loads(raw_json)
    except:
        raise HTTPException(status_code=422, detail="AI returned invalid JSON. Please retry.")

    # Wrap into a proper TestCase object
    testcase_seq = await get_next_sequence("testcase_id","TC")
    testcase_id = f"TC{testcase_seq:04d}"

    testcase_doc = {
        "testcase_id": testcase_id,
        "scenario_id": scenario_id,
        "title": scenario.get("title") + " - Auto Generated",
        "steps": steps_json,
        "status": "draft",
        "created_by": current_user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    # 5. Save to DB
    result = await db["testcases"].insert_one(testcase_doc)
    testcase_doc["id"] = str(result.inserted_id)

    return {
        "message": "Testcase generated successfully",
        "testcase": testcase_doc
    }
