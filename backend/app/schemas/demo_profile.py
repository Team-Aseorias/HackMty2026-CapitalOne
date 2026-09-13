from typing import Literal

from pydantic import BaseModel, Field


class DemoProfileOut(BaseModel):
    key: str
    label: str
    description: str
    resolved_verifications: int = Field(ge=0)
    reported_abandons: int = Field(ge=0)
    history_source: Literal["controlled_demo_plus_reported_session"] = (
        "controlled_demo_plus_reported_session"
    )


class DemoPurchaseAttemptIn(BaseModel):
    merchant: str = Field(min_length=1, max_length=200)
    amount: float = Field(gt=0, le=1_000_000, allow_inf_nan=False)
