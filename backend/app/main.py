import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app.db.mongo import close_client, ensure_indexes, is_configured, ping
from app.routers import dashboard, decisions, demo_profiles, evaluations, purchase_attempts
from app.core.config import settings
from app.core.security import require_api_key
from app.repositories.decision_repository import PersistenceUnavailable
from app.services.causal_service import _default_learner
from app.services.risk_service import _risk_model

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.models_ready = False
    if not settings.demo_mode and (not settings.api_key or not is_configured()):
        raise RuntimeError("Strict mode requires MongoDB and BACKEND_API_KEY")
    try:
        if is_configured():
            if await ping():
                await ensure_indexes()
            elif not settings.demo_mode:
                raise RuntimeError("MongoDB unavailable in strict mode")
            else:
                logger.warning("MongoDB unavailable; demo inference may use memory")
        await run_in_threadpool(_risk_model)
        await run_in_threadpool(_default_learner)
        application.state.models_ready = True
        yield
    finally:
        application.state.models_ready = False
        await close_client()


app = FastAPI(title="ANCLA API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(purchase_attempts.router, dependencies=[Depends(require_api_key)])
app.include_router(decisions.router, dependencies=[Depends(require_api_key)])
app.include_router(dashboard.router, dependencies=[Depends(require_api_key)])
app.include_router(evaluations.router, dependencies=[Depends(require_api_key)])
app.include_router(demo_profiles.router, dependencies=[Depends(require_api_key)])


@app.exception_handler(PersistenceUnavailable)
async def persistence_unavailable(_, exc: PersistenceUnavailable):
    return JSONResponse(status_code=503, content={"detail": "Decision storage unavailable; retry after recovery"})


@app.get("/ready", tags=["health"])
async def ready():
    models_ready = getattr(app.state, "models_ready", False)
    database_ready = await ping() if is_configured() else False
    ok = models_ready and (settings.demo_mode or database_ready)
    return JSONResponse(status_code=200 if ok else 503, content={
        "ready": ok, "models_ready": models_ready, "database_connected": database_ready,
        "demo_mode": settings.demo_mode, "model_version": "synthetic-v3",
    })


@app.get("/health", tags=["health"])
async def health() -> dict[str, str | bool]:
    configured = is_configured()
    connected = await ping() if configured else False
    return {
        "status": "ok" if connected or not configured else "degraded",
        "database_configured": configured,
        "database_connected": connected,
    }
