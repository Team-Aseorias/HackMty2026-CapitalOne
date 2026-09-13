from typing import Literal
from pydantic import BaseModel, Field


class SafetyCheck(BaseModel):
    code: str
    observed: float
    threshold: float
    triggered: bool


class PersonalizationEvidence(BaseModel):
    resolved_verifications: int
    reported_abandons: int
    smoothed_abandonment_rate: float
    minimum_history: int
    prior_alpha: int = 1
    prior_beta: int = 5
    source: str = "consumer_reports_not_adjudicated_fraud_labels"


class ActivityEvidence(BaseModel):
    window_seconds: int
    prior_attempts: int
    prior_verify_abandons: int
    includes_current_attempt: bool = False


class DecisionOut(BaseModel):
    id: str | None = None
    demo_profile_key: str | None = None
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
    policy_version: str = "safety-v2"
    safety_checks: list[SafetyCheck] = Field(default_factory=list)
    cost_preferred_action: Literal["allow", "verify"] | None = None
    personalization_evidence: PersonalizationEvidence | None = None
    recent_activity: ActivityEvidence | None = None
    model_warnings: list[str] = Field(default_factory=list)
    # Completion/abandonment never establishes whether a purchase was fraud.
    fraud_status: Literal["unknown"] = "unknown"
