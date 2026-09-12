from pydantic import BaseModel


class PolicyEvaluation(BaseModel):
    policy: str
    expected_cost: float
    verification_rate: float
