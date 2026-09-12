from fastapi import APIRouter

from app.schemas.metrics import DashboardMetrics
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/metrics", response_model=DashboardMetrics)
async def metrics() -> DashboardMetrics:
    return MetricsService().dashboard()
