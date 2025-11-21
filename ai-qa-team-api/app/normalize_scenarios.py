import asyncio
import json
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# MONGO_URI = "YOUR_MONGO_URI_HERE"
# DB_NAME = "YOUR_DB_NAME_HERE"

MONGO_URI="mongodb+srv://sramraj_db_user:jW7k1AtBTyzFNQRv@cluster0.czo2fqu.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
MONGO_DB="Cluster0"

client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB]

# ---------------------------------------------------------
# NORMALIZERS
# ---------------------------------------------------------
def normalize_text(value):
    """Ensure value becomes a clean string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return " ".join(str(x) for x in value)
    return str(value)


def normalize_step(raw, idx):
    """Normalize a step into the expected structure."""
    
    # Case 1: Already correct dict with correct types
    if isinstance(raw, dict):
        return {
            "step_id": raw.get("step_id", f"STEP{idx:03d}"),
            "category": normalize_text(raw.get("category", "General")),
            "action": normalize_text(raw.get("action", "Undefined action")),
            "expected": normalize_text(raw.get("expected", "No expected result")),
        }

    # Case 2: Raw string
    if isinstance(raw, str):
        return {
            "step_id": f"STEP{idx:03d}",
            "category": "General",
            "action": normalize_text(raw),
            "expected": "Expected result not provided",
        }

    # Case 3: Raw list (join as text)
    if isinstance(raw, list):
        return {
            "step_id": f"STEP{idx:03d}",
            "category": "General",
            "action": normalize_text(" → ".join(str(x) for x in raw)),
            "expected": "Expected result not provided",
        }

    # Fallback
    return {
        "step_id": f"STEP{idx:03d}",
        "category": "General",
        "action": normalize_text(raw),
        "expected": "Expected result not provided",
    }


# ---------------------------------------------------------
# CLEANUP: SCENARIOS
# ---------------------------------------------------------
async def fix_scenarios():
    print("\n🔧 Fixing Scenarios ...")

    cursor = db["scenarios"].find({})
    count = 0

    async for doc in cursor:
        doc_id = doc["_id"]
        scenario_id = doc.get("scenario_id")

        raw_steps = doc.get("steps", [])

        # normalize all steps
        normalized_steps = [
            normalize_step(step, idx)
            for idx, step in enumerate(raw_steps, start=1)
        ]

        # generated_by_agent must be string
        gba = doc.get("generated_by_agent")
        if isinstance(gba, bool):
            gba = None
        elif gba is not None:
            gba = str(gba)

        await db["scenarios"].update_one(
            {"_id": doc_id},
            {
                "$set": {
                    "steps": normalized_steps,
                    "generated_by_agent": gba,
                }
            },
        )

        print(f"✔ Scenario {scenario_id} repaired")
        count += 1

    print(f"🎉 Scenario cleanup complete — fixed {count}")


# ---------------------------------------------------------
# CLEANUP: STORIES (light cleanup)
# ---------------------------------------------------------
async def fix_stories():
    print("\n🔧 Fixing Stories ...")

    cursor = db["stories"].find({})
    count = 0

    async for doc in cursor:
        doc_id = doc["_id"]
        tags = doc.get("tags", [])
        if not isinstance(tags, list):
            tags = [str(tags)]

        await db["stories"].update_one(
            {"_id": doc_id},
            {"$set": {"tags": tags}},
        )

        count += 1

    print(f"🎉 Story cleanup complete — fixed {count}")


# ---------------------------------------------------------
# CLEANUP: PROJECTS
# ---------------------------------------------------------
async def fix_projects():
    print("\n🔧 Fixing Projects ...")

    cursor = db["projects"].find({})
    count = 0

    async for doc in cursor:
        doc_id = doc["_id"]

        agents = doc.get("agent_identities", {})
        

        fixed_agents = {
            "recorder": agents.get("recorder", "Recorder Agent"),
            "scenario_builder": agents.get("scenario_builder", "Scenario Builder"),
            "test_generator": agents.get("test_generator", "Test Generator"),
            "executor": agents.get("executor", "Executor Agent"),
        }

        await db["projects"].update_one(
            {"_id": doc_id},
            {"$set": {"agent_identities": fixed_agents}},
        )

        count += 1

    print(f"🎉 Project cleanup complete — fixed {count}")


# ---------------------------------------------------------
# RUN ALL MIGRATIONS
# ---------------------------------------------------------
async def run_full_cleanup():
    print("\n🚀 Starting Full Database Cleanup ...\n")
    await fix_scenarios()
    await fix_stories()
    await fix_projects()
    print("\n✨ ALL CLEANUP COMPLETED SUCCESSFULLY ✨\n")


if __name__ == "__main__":
    asyncio.run(run_full_cleanup())