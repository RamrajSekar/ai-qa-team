from fastapi import FastAPI
from contextlib import asynccontextmanager
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from app.db.connection import db
from app.utils.redis_client import check_redis_connection
from app.routes import story_routes,auth_routes, subscription_routes, test_execution_routes,scenario_routes, testcase_routes, project_routes, recorder_routes, environment_routes,health_routes, user_routes
from app.utils.logger import logger
from app.middleware.error_handler import jwt_exception_handler
from app.config import settings
from app.db.init_indexes import init_indexes

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    try:
        print("🚀 App starting – creating MongoDB indexes")
        await init_indexes()
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


# ✅ Register global middleware
app.middleware("http")(jwt_exception_handler)

# ✅ CORS Setup
origins = [
    "http://127.0.0.1:8000",  # Swagger docs
    "http://localhost:8000",
    "http://127.0.0.1:3000",  # React frontend (if applicable)
    "http://localhost:3000",
    "https://ai-qa-team.vercel.app/"
]

# ✅ Add session middleware (REQUIRED for OAuth)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # Or use ["*"] during development
    # allow_origins=["https://ai-qa-team.vercel.app/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Session Middleware (for OAuth)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.jwt_secret_key
)


# === Routers ===
app.include_router(auth_routes.router)
app.include_router(health_routes.router)
app.include_router(user_routes.router)
app.include_router(subscription_routes.router)
app.include_router(project_routes.router)
app.include_router(environment_routes.router)
app.include_router(story_routes.router)
app.include_router(recorder_routes.router)
app.include_router(scenario_routes.router)
app.include_router(test_execution_routes.router)
app.include_router(testcase_routes.router)

# === Base Routes ===
@app.get("/")
async def root():
    return {"message": "🚀 AI QA Team backend is running!"}
