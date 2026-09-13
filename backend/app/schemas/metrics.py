from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    attempts: int = 0
    allowed: int = 0
    verified: int = 0
    completed: int = 0
    abandoned: int = 0
    blocked: int = 0
    pending: int = 0
    verification_rate: float = 0.0
    average_expected_cost: float | None = None
    source: str = "memory"
