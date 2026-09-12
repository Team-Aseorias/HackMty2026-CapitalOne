"""Conditional outcome models for randomized allow/verify training data.

Fraud loss and voluntary abandonment are different outcomes. Each treatment
arm learns its own fraud-success probability and its own legitimate-customer
abandonment probability. Expected cost combines those probabilities with the
current configured costs. No simulator oracle field is used for fitting.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.ml.probability_models import RegularizedProbabilityModel, feature_matrix
from app.ml.simulator import FEATURE_NAMES


def _positive(model: Any, matrix) -> list[float]:
    classes = list(model.classes_)
    return [float(row[classes.index(True)]) if True in classes else 0.0
            for row in model.predict_proba(matrix)]


@dataclass
class TLearner:
    allow_model: Any
    verify_model: Any
    allow_completion_model: Any
    verify_completion_model: Any
    training_rows: int = 0
    model_version: str = "synthetic-v3"

    def expected_costs(self, features: dict) -> tuple[float, float]:
        return self.predict_many([features])[0][:2]

    def completion_probabilities(self, features: dict) -> tuple[float, float]:
        """Completion probability conditional on a legitimate transaction."""
        return self.predict_many([features])[0][2:]

    def predict_many(self, features: list[dict]) -> list[tuple[float, float, float, float]]:
        if not features:
            return []
        # Gating sparse histories also applies to direct/batch model callers.
        normalized = [
            {**row, "prior_verify_abandonment_rate": 1 / 6}
            if row.get("prior_verifications", 0) < settings.min_personalization_history
            else row for row in features
        ]
        fraud_matrix = feature_matrix(normalized, personalization=False)
        abandonment_matrix = feature_matrix(normalized)
        fraud_allow = _positive(self.allow_model, fraud_matrix)
        fraud_verify = _positive(self.verify_model, fraud_matrix)
        abandon_allow = _positive(self.allow_completion_model, fraud_matrix)
        abandon_verify = _positive(self.verify_completion_model, abandonment_matrix)
        results = []
        for row, fa, fv, aa, av in zip(normalized, fraud_allow, fraud_verify, abandon_allow, abandon_verify):
            amount = float(row.get("amount", 0))
            if amount < 0:
                raise ValueError("Amount must not be negative")
            # Monotonic constraints on the verify abandonment head ensure that
            # more abandonment history cannot increase verification completion.
            allow_cost = amount * fa + (1 - fa) * aa * amount * settings.abandonment_cost_rate
            verify_cost = amount * fv + settings.verify_cost + (1 - fa) * av * amount * settings.abandonment_cost_rate
            results.append((allow_cost, verify_cost, 1 - aa, 1 - av))
        return results


def fit_t_learner(records: list[dict]) -> TLearner:
    """Only observed labels under each randomized treatment arm are consumed.

    Fraud labels must come from adjudicated historical training data. We cannot
    infer voluntary abandonment from a generic failed/blocked fraud payment.
    """
    models = []
    for treatment in ("allow", "verify"):
        arm = [row for row in records if row["treatment"] == treatment]
        genuine = [row for row in arm if not row["fraud"]]
        if len(arm) < 30 or len(genuine) < 20:
            raise ValueError("Training requires at least 30 observations and 20 legitimate transactions per arm")
        fraud_success = [bool(row["fraud"] and row["observed_completed"]) for row in arm]
        fraud_model = RegularizedProbabilityModel().fit(
            feature_matrix(arm, personalization=False), fraud_success,
        )
        # Only resolved genuine purchases train the voluntary-abandonment head.
        dropout_model = RegularizedProbabilityModel(
            monotone_index=FEATURE_NAMES.index("prior_verify_abandonment_rate") if treatment == "verify" else None,
        ).fit(feature_matrix(genuine, personalization=treatment == "verify"),
              [not row["observed_completed"] for row in genuine])
        models.append((fraud_model, dropout_model))
    return TLearner(
        allow_model=models[0][0], verify_model=models[1][0],
        allow_completion_model=models[0][1], verify_completion_model=models[1][1],
        training_rows=len(records),
    )
