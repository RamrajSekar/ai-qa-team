from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.connection import db
from app.utils.redis_client import check_redis_connection
from app.routes import story_routes
from app.utils.logger import logger



@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    try:
        collections = await db.list_collection_names()
        logger.info(f"✅ MongoDB connected. Collections: {collections}")
    except Exception as e:
        logger.info(f"❌ MongoDB connection failed: {e}")
        raise e

    try:
        check_redis_connection()
    except Exception as e:
        logger.info(f"⚠️ Redis connection skipped or failed: {e}")

    yield  # hand control back to FastAPI while app runs

    # --- Shutdown ---
    logger.info("👋 Shutting down AI QA Team API...")


# === Initialize App ===
app = FastAPI(title="AI QA Team API", lifespan=lifespan)


# === Routers ===
app.include_router(story_routes.router)


# === Base Routes ===
@app.get("/")
async def root():
    return {"message": "🚀 AI QA Team backend is running!"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}
