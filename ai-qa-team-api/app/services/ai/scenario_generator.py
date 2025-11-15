from app.services.ai.provider_factory import get_ai_provider
from app.db.connection import db
from bson.objectid import ObjectId

async def generate_scenarios_from_story(story, project_id):
    provider = get_ai_provider()

    # Fetch project agent identity
    project = await db["projects"].find_one({"_id": ObjectId(project_id)})
    agent_name = (
        project.get("agent_identities", {})
               .get("scenario_builder", "Scenario Builder")
    )

    prompt = f"""
    You are an AI Scenario Generator named {agent_name}.

    Generate structured test scenarios for this story:
    Title: {story.get("title")}
    Description: {story.get("description")}

    Return JSON only:
    [
      {{
        "title": "...",
        "description": "...",
        "steps": ["...", "..."]
      }}
    ]
    """

    raw = await provider.generate(prompt)
    return raw
