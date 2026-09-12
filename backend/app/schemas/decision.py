from typing import Literal
from pydantic import BaseModel, Field


class DecisionOut(BaseModel):
    id: str | None = None
    decision: Literal["allow", "verify"]
    risk_score: float = Field(ge=0, le=1)
    reason: str
    estimated_cost_allow: float | None = Field(default=None, ge=0)
    estimated_cost_verify: float | None = Field(default=None, ge=0)
    uplift: float | None = None
    allow_completion_probability: float | None = Field(default=None, ge=0, le=1)
    verify_completion_probability: float | None = Field(default=None, ge=0, le=1)
    incremental_abandonment_probability: float | None = Field(default=None, ge=0, le=1)
    context_source: Literal["nessie", "local"] = "local"
