"""Training support checks, not a claim of real-world calibration."""
from functools import lru_cache

from app.ml.simulator import FEATURE_NAMES, generate_synthetic_data
from app.schemas.decision import PersonalizationEvidence
from app.core.config import settings


@lru_cache(maxsize=1)
def training_bounds():
    rows = generate_synthetic_data(rows=12000, seed=2026)
    bounds = {name: (min(row[name] for row in rows), max(row[name] for row in rows))
              for name in FEATURE_NAMES}
    # Respect known generator boundaries: a continuous random sample seldom
    # contains its exact endpoints. A usual purchase with zero deviation must
    # not be flagged just because the sampled minimum was slightly above zero.
    bounds.update({
        "amount": (5, 1500), "average_purchase_amount": (8, 600),
        "recent_spend": (0, 4000),
        "prior_verify_abandonment_rate": (1 / 18, 13 / 18),
        "distance_from_usual": (0, bounds["distance_from_usual"][1]),
        "amount_zscore": (0, bounds["amount_zscore"][1]),
    })
    return bounds


def diagnostics(features: dict) -> tuple[PersonalizationEvidence, list[str]]:
    warnings = ["synthetic_training_only", "allow_completion_simulator_assumption",
                "outcomes_are_not_fraud_labels"]
    for name, (low, high) in training_bounds().items():
        if not low <= features[name] <= high:
            warnings.append("outside_training_range:" + name)
    evidence = PersonalizationEvidence(
        resolved_verifications=int(features["prior_verifications"]),
        reported_abandons=int(features["prior_verify_abandons"]),
        smoothed_abandonment_rate=features["prior_verify_abandonment_rate"],
        minimum_history=settings.min_personalization_history,
    )
    return evidence, warnings
