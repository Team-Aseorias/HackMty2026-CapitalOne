import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.mongo import close_client, ensure_indexes, is_configured, ping
from app.routers import dashboard, decisions, evaluations, purchase_attempts

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if is_configured():
        if await ping():
            try:
                await ensure_indexes()
            except Exception as exc:
                logger.warning("Could not initialize MongoDB indexes: %s", exc)
        else:
            logger.warning("MongoDB is configured but unavailable; using local fallback")
    yield
    await close_client()


app = FastAPI(title="ANCLA API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(purchase_attempts.router)
app.include_router(decisions.router)
app.include_router(dashboard.router)
app.include_router(evaluations.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str | bool]:
    configured = is_configured()
    connected = await ping() if configured else False
    return {
        "status": "ok" if connected or not configured else "degraded",
        "database_configured": configured,
        "database_connected": connected,
    }
