from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    attempts: int = 0
    allowed: int = 0
    verified: int = 0
