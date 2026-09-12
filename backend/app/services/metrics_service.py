from app.schemas.metrics import DashboardMetrics
from app.repositories.decision_repository import DecisionRepository


class MetricsService:
    async def dashboard(self) -> DashboardMetrics:
        return DashboardMetrics(**await DecisionRepository().metrics())
