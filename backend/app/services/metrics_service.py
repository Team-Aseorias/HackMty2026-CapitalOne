from app.schemas.metrics import DashboardMetrics
from app.repositories.decision_repository import DecisionRepository


class MetricsService:
    def dashboard(self) -> DashboardMetrics:
        # Kept synchronous for the existing lightweight dashboard contract.
        # Operational counters can be served from Mongo aggregation in deploy.
        return DashboardMetrics()
