from datetime import datetime
from pydantic import AwareDatetime, BaseModel, Field


class PurchaseAttemptIn(BaseModel):
    customer_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    account_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    merchant: str = Field(min_length=1, max_length=200)
    merchant_id: str | None = None
    amount: float = Field(gt=0, le=1_000_000, allow_inf_nan=False)
    occurred_at: AwareDatetime | None = None
