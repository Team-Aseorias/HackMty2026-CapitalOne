"""Reproducible randomized data for the offline causal evaluation.

The fields ending in ``_allow`` and ``_verify`` are *oracle-only* potential
outcomes.  Training must use only ``observed_cost``.  This lets the demo show
an honest policy comparison without claiming that we observe counterfactuals
in Nessie.
"""

from __future__ import annotations

import math
import random

from app.core.config import settings

FEATURE_NAMES = (
    "amount",
    "hour",
    "weekday",
    "merchant_novelty",
    "recent_purchase_count",
    "recent_spend",
    "account_age_days",
    "distance_from_usual",
    "average_purchase_amount",
    "amount_zscore",
    "prior_verifications",
    "prior_verify_abandonment_rate",
)

RISK_FEATURE_NAMES = tuple(
    name for name in FEATURE_NAMES
    if name not in {"prior_verifications", "prior_verify_abandonment_rate"}
)


def _sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-max(-30, min(30, value))))


def generate_synthetic_data(rows: int = 1_000, seed: int = 2026) -> list[dict]:
    """Return randomized treatment records with latent fraud and outcomes."""
    rng = random.Random(seed)
    result: list[dict] = []
    for _ in range(rows):
        # Purchase values have a long tail; log-uniform sampling also provides
        # enough low-value examples for the outcome models to learn when the
        # maximum possible fraud loss is below verification friction.
        typical_amount = math.exp(rng.uniform(math.log(8), math.log(600)))
        amount = round(min(1_500, max(5, typical_amount * math.exp(rng.gauss(0, 0.75)))), 2)
        hour = rng.randrange(24)
        merchant_novelty = float(rng.random() < 0.45)
        recent_count = rng.randrange(0, 16)
        recent_spend = round(rng.uniform(0, 4_000), 2)
        account_age = rng.randrange(1, 3_650)
        distance = abs(amount - typical_amount) / max(typical_amount, 1) * 10
        latent_risk = rng.random()
        # This represents a stable but unobserved tolerance to interruption.
        # The model sees only its observable historical proxy below.
        friction_sensitivity = rng.betavariate(2, 5)
        prior_verifications = rng.randrange(0, 13)
        historical_abandonment_probability = _sigmoid(-2.8 + 4.0 * friction_sensitivity)
        prior_abandons = sum(
            rng.random() < historical_abandonment_probability
            for _ in range(prior_verifications)
        )
        # Empirical-Bayes smoothing avoids treating one abandoned verification
        # as proof that this customer always abandons.
        prior_abandonment_rate = (
            (prior_abandons + 1) / (prior_verifications + 6)
            if prior_verifications >= settings.min_personalization_history else 1 / 6
        )
        amount_zscore = abs(math.log(amount / typical_amount)) / 0.75
        fraud_probability = _sigmoid(
            -4.4 + 2.0 * merchant_novelty + 0.0012 * amount
            + 0.016 * distance + 2.4 * latent_risk + (0.7 if hour < 6 else 0)
        )
        fraud = rng.random() < fraud_probability

        # Verification is more effective for unusual, high-risk attempts, but
        # has a non-zero fraud bypass rate and legitimate-user abandonment.
        fraud_bypass = _sigmoid(-1.7 + 1.1 * latent_risk - 0.8 * merchant_novelty)
        legitimate_abandonment = _sigmoid(
            -4.2 + 1.1 * merchant_novelty + 0.012 * distance
            + 3.0 * prior_abandonment_rate + 0.75 * amount_zscore
        )
        allow_fraud_loss = amount if fraud else 0.0
        verify_fraud_loss = amount if fraud and rng.random() < fraud_bypass else 0.0
        abandoned = not fraud and rng.random() < legitimate_abandonment
        verify_completed = bool(verify_fraud_loss > 0 or (not fraud and not abandoned))
        allow_cost = allow_fraud_loss
        verify_cost = (
            verify_fraud_loss
            + settings.verify_cost
            + (amount * settings.abandonment_cost_rate if abandoned else 0.0)
        )
        treatment = "verify" if rng.random() < 0.5 else "allow"  # randomized propensity = 0.5
        result.append({
            "amount": amount,
            "hour": hour,
            "weekday": rng.randrange(7),
            "merchant_novelty": merchant_novelty,
            "recent_purchase_count": recent_count,
            "recent_spend": recent_spend,
            "account_age_days": account_age,
            "distance_from_usual": distance,
            "average_purchase_amount": typical_amount,
            "amount_zscore": amount_zscore,
            "prior_verifications": prior_verifications,
            "prior_verify_abandonment_rate": prior_abandonment_rate,
            "fraud": fraud,
            "treatment": treatment,
            "observed_cost": verify_cost if treatment == "verify" else allow_cost,
            "observed_completed": verify_completed if treatment == "verify" else True,
            "cost_allow": allow_cost,
            "cost_verify": verify_cost,
            "fraud_loss_allow": allow_fraud_loss,
            "fraud_loss_verify": verify_fraud_loss,
            "completed_allow": True,
            "completed_verify": verify_completed,
        })
    return result
