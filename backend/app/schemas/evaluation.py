from pydantic import BaseModel


class PolicyEvaluation(BaseModel):
    policy: str
    expected_cost: float
    verification_rate: float
    legitimate_completion_rate: float = 0.0
    legitimate_abandonment_rate: float = 0.0
    fraud_loss_per_attempt: float = 0.0
    fraud_capture_rate: float = 0.0
    safety_violations: int = 0
    cost_standard_error: float = 0.0
    seed: int = 2027
    sample_size: int = 1000
    data_source: str = "synthetic"
    model_version: str = "synthetic-v3"
