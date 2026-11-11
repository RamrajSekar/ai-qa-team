import asyncio
from datetime import datetime, timezone
from app.db.connection import db
from app.models.subscription import Subscription
from app.models.user_model import OnboardingModel

"""
This script fixes OAuth users missing subscription/onboarding.

It will:
 - Detect users with Google/GitHub OAuth
 - Add subscription (free plan)
 - Add usage + limits
 - Add onboarding structure
 - Add created_at if missing
 - Safely skip users already migrated
"""


async def migrate_oauth_users():
    print("\n🔍 Starting OAuth user migration...\n")

    # Find users missing subscription OR onboarding
    cursor = db["users"].find({
        "$or": [
            {"subscription": {"$exists": False}},
            {"onboarding": {"$exists": False}},
            {"created_at": {"$exists": False}},
        ]
    })

    updated_count = 0
    async for user in cursor:
        email = user.get("email")
        provider = user.get("provider")

        if provider not in ("google", "github"):
            # Skip non-oauth users
            continue

        print(f"➡ Fixing OAuth user: {email} ({provider})")

        updates = {}

        # 1️⃣ Add subscription if missing
        if "subscription" not in user:
            sub = Subscription(plan="free")
            sub.apply_plan_defaults()
            updates["subscription"] = sub.model_dump()
            print("   ✔ Added subscription.free")

        # 2️⃣ Add onboarding if missing
        if "onboarding" not in user:
            onboarding = OnboardingModel()
            updates["onboarding"] = onboarding.model_dump()
            print("   ✔ Added onboarding structure")

        # 3️⃣ Add created_at if missing
        if "created_at" not in user:
            updates["created_at"] = datetime.now(timezone.utc)
            print("   ✔ Added created_at timestamp")

        # 4️⃣ Ensure usage exists (in case subscription existed but was incomplete)
        if "subscription" in user:
            sub = user["subscription"]
            if "usage" not in sub:
                updates["subscription.usage"] = Subscription(plan="free").usage_defaults()
                print("   ✔ Repaired subscription.usage")

            if "limits" not in sub:
                updates["subscription.limits"] = Subscription(plan="free").limits_defaults()
                print("   ✔ Repaired subscription.limits")

        if updates:
            await db["users"].update_one({"_id": user["_id"]}, {"$set": updates})
            updated_count += 1
            print("   ✅ User updated.\n")
        else:
            print("   ✔ User already has all required fields.\n")

    print(f"🎉 Migration complete. Updated {updated_count} OAuth users.\n")


if __name__ == "__main__":
    asyncio.run(migrate_oauth_users())
