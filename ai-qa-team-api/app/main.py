from fastapi import FastAPI, Depends, Response
from contextlib import asynccontextmanager
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from app.db.connection import db
from app.utils.redis_client import check_redis_connection
from app.routes import story_routes,auth_routes, subscription_routes, test_execution_routes,scenario_routes, testcase_routes, project_routes, recorder_routes, environment_routes,health_routes, user_routes, integration_routes, repository_routes, project_team_routes, ai_configuration_routes, platform_admin_routes
from app.utils.logger import logger
from app.middleware.error_handler import jwt_exception_handler
from app.config import settings
from app.db.init_indexes import init_indexes
from app.utils.feature_flags import feature_required
from app.utils.auth_cookies import session_cookie_options

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
local_origins = [
    "http://127.0.0.1:8000",  # Swagger docs
    "http://localhost:8000",
    "http://127.0.0.1:3000",  # React frontend (if applicable)
    "http://localhost:3002",
    "http://172.20.10.6:3002",
]

configured_origins = [
    origin.strip().rstrip("/")
    for origin in (settings.cors_origins or "").split(",")
    if origin.strip()
]
origins = list(dict.fromkeys([*local_origins, *configured_origins]))

# ✅ Add session middleware (REQUIRED for OAuth)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Session Middleware (for OAuth)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.jwt_secret_key,
    **session_cookie_options(),
)


# === Routers ===
app.include_router(auth_routes.router)
app.include_router(health_routes.router)
app.include_router(user_routes.router)
app.include_router(subscription_routes.router)
app.include_router(project_routes.router)
app.include_router(environment_routes.router)
app.include_router(
    story_routes.router,
    dependencies=[Depends(feature_required("story_management"))],
    include_in_schema=settings.features.story_management,
)
app.include_router(
    recorder_routes.router,
    dependencies=[Depends(feature_required("recorder"))],
    include_in_schema=settings.features.recorder,
)
app.include_router(
    scenario_routes.router,
    dependencies=[Depends(feature_required("scenario_generation"))],
    include_in_schema=settings.features.scenario_generation,
)
app.include_router(test_execution_routes.router)
app.include_router(testcase_routes.router)
app.include_router(integration_routes.router)
app.include_router(repository_routes.router)
app.include_router(project_team_routes.router)
app.include_router(ai_configuration_routes.router)
app.include_router(platform_admin_routes.router)

# === Base Routes ===
@app.get("/features", response_model=dict[str, bool], tags=["Features"])
async def get_features(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return settings.features.model_dump()


@app.get("/")
async def root():
    return {"message": "🚀 AI QA Team backend is running!"}
