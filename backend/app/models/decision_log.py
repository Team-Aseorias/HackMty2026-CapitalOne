from typing import Literal, TypedDict


class DecisionLogDocument(TypedDict, total=False):
    transaction_id: str
    decision: Literal["allow", "verify"]
    risk_score: float
    outcome: str
