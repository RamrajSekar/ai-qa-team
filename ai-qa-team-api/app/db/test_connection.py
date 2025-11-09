import asyncio
from app.db.connection import db
from pymongo.errors import ConnectionFailure
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))



async def test_connection():
    try:
        collections = await db.list_collection_names()
        print("✅ Connected successfully. Collections:", collections)
    except ConnectionFailure as e:
        print("❌ MongoDB connection failed:", e)
    except Exception as e:
        print("⚠️ Unexpected error:", e)

if __name__ == "__main__":
    asyncio.run(test_connection())
