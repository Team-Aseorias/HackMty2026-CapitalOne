from datetime import datetime
from pydantic import BaseModel, Field


class PurchaseAttemptIn(BaseModel):
    customer_id: str
    account_id: str
    merchant: str
    merchant_id: str | None = None
    amount: float = Field(gt=0)
    occurred_at: datetime | None = None
