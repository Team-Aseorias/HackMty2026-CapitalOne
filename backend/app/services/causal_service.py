"""Causal treatment-effect service.

Positive uplift means that verification lowers estimated net cost relative to
allowing the same attempt.  It is an estimate, never a per-transaction fact.
"""

from functools import lru_cache

from app.ml.simulator import generate_synthetic_data
from app.ml.train_causal import TLearner, fit_t_learner


@lru_cache(maxsize=1)
def _default_learner() -> TLearner:
    # In deployment replace this bootstrap with a versioned serialized artifact
    # trained from randomized/appropriately adjusted decision logs.
    return fit_t_learner(generate_synthetic_data(rows=12_000, seed=2026))


class CausalService:
    def __init__(self, learner: TLearner | None = None) -> None:
        self.learner = learner

    def expected_costs(self, features: dict) -> tuple[float, float]:
        return (self.learner or _default_learner()).expected_costs(features)

    def completion_probabilities(self, features: dict) -> tuple[float, float]:
        """P(legitimate customer completes) under allow and verify."""
        return (self.learner or _default_learner()).completion_probabilities(features)

    def predict(self, features: dict) -> tuple[float, float, float, float]:
        return (self.learner or _default_learner()).predict_many([features])[0]

    def uplift(self, features: dict) -> float:
        """Estimated incremental benefit: E[cost|allow] - E[cost|verify]."""
        if not features:
            return 0.0
        allow_cost, verify_cost = self.expected_costs(features)
        return allow_cost - verify_cost
