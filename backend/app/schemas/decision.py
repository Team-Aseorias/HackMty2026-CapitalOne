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
    allow_completion_probability: float | None = Field(default=None, ge=0, le=1, description="Completion probability conditional on a legitimate transaction, under allow")
    verify_completion_probability: float | None = Field(default=None, ge=0, le=1, description="Completion probability conditional on a legitimate transaction, under verify")
    incremental_abandonment_probability: float | None = Field(default=None, ge=0, le=1)
    context_source: Literal["nessie", "local"] = "local"
    safety_override: bool = False
    personalization_applied: bool = False
    model_version: str = "synthetic-v3"
    persistence_source: Literal["mongo", "memory"] = "memory"
