from app.services.causal_service import CausalService
from app.services.feature_service import FeatureService


def test_causal_service_returns_uplift() -> None:
    assert CausalService().uplift({}) == 0.0


def test_verification_completion_is_personalized_from_prior_abandonment() -> None:
    attempt = {"amount": 350, "merchant": "new-shop"}
    features = FeatureService()
    new_customer = features.build(attempt, [])
    friction_sensitive = features.build(
        attempt,
        [],
        decision_history=[{"decision": "verify", "outcome": "abandoned"} for _ in range(12)],
    )
    causal = CausalService()
    _, new_verify_completion = causal.completion_probabilities(new_customer)
    _, sensitive_verify_completion = causal.completion_probabilities(friction_sensitive)
    assert sensitive_verify_completion < new_verify_completion
    assert causal.uplift(friction_sensitive) < causal.uplift(new_customer)
