"""Train the two outcome models used by ANCLA's T-learner."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from app.ml.simulator import FEATURE_NAMES


def _matrix(records: list[dict]) -> list[list[float]]:
    return [[float(record.get(name, 0.0)) for name in FEATURE_NAMES] for record in records]


@dataclass
class StructuralFallbackRegressor:
    """Local fallback preserving heterogeneous treatment effects without sklearn."""

    treatment: str

    def fit(self, _x: list[list[float]], _y: list[float]) -> "StructuralFallbackRegressor":
        return self

    def predict(self, rows: list[list[float]]) -> list[float]:
        output: list[float] = []
        for row in rows:
            values = dict(zip(FEATURE_NAMES, row))
            amount = values["amount"]
            raw_risk = -4.4 + 2 * values["merchant_novelty"] + .0012 * amount + .016 * values["distance_from_usual"]
            raw_risk += .7 if values["hour"] < 6 else 0
            fraud_probability = 1 / (1 + math.exp(-max(-30, min(30, raw_risk))))
            if self.treatment == "allow":
                output.append(fraud_probability * amount)
                continue
            bypass_probability = 1 / (1 + math.exp(-(-1.7 - .8 * values["merchant_novelty"])))
            abandonment = _verify_abandonment_probability(values)
            output.append(fraud_probability * bypass_probability * amount + 5 + (1 - fraud_probability) * abandonment * amount * .15)
        return output


def _verify_abandonment_probability(values: dict[str, float]) -> float:
    score = (
        -4.2 + 1.1 * values["merchant_novelty"]
        + .012 * values["distance_from_usual"]
        + 3.0 * values["prior_verify_abandonment_rate"]
        + .75 * values["amount_zscore"]
    )
    return 1 / (1 + math.exp(-max(-30, min(30, score))))


@dataclass
class StructuralFallbackClassifier:
    treatment: str

    def fit(self, _x: list[list[float]], _y: list[bool]) -> "StructuralFallbackClassifier":
        return self

    def predict_proba(self, rows: list[list[float]]) -> list[list[float]]:
        probabilities: list[list[float]] = []
        for row in rows:
            if self.treatment == "allow":
                probabilities.append([0.0, 1.0])
            else:
                completed = 1 - _verify_abandonment_probability(dict(zip(FEATURE_NAMES, row)))
                probabilities.append([completed, 1 - completed])
        return probabilities


@dataclass
class TLearner:
    allow_model: Any
    verify_model: Any
    allow_completion_model: Any
    verify_completion_model: Any

    def expected_costs(self, features: dict) -> tuple[float, float]:
        values = _matrix([features])
        return (
            max(0.0, float(self.allow_model.predict(values)[0])),
            max(0.0, float(self.verify_model.predict(values)[0])),
        )

    def completion_probabilities(self, features: dict) -> tuple[float, float]:
        values = _matrix([features])
        return (
            _positive_probability(self.allow_completion_model, values),
            _positive_probability(self.verify_completion_model, values),
        )


def _positive_probability(model: Any, values: list[list[float]]) -> float:
    probabilities = model.predict_proba(values)[0]
    classes = getattr(model, "classes_", [False, True])
    try:
        positive_index = list(classes).index(True)
    except ValueError:
        return 0.0
    return min(1.0, max(0.0, float(probabilities[positive_index])))


def fit_t_learner(records: list[dict]) -> TLearner:
    """Fit E[Y | X, A=allow] and E[Y | X, A=verify] on observed outcomes."""
    allow = [record for record in records if record["treatment"] == "allow"]
    verify = [record for record in records if record["treatment"] == "verify"]
    try:
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    except ImportError:
        # Keeps the API runnable before optional ML dependencies are installed.
        allow_model = StructuralFallbackRegressor("allow")
        verify_model = StructuralFallbackRegressor("verify")
        allow_completion_model = StructuralFallbackClassifier("allow")
        verify_completion_model = StructuralFallbackClassifier("verify")
    else:
        allow_model = RandomForestRegressor(
            n_estimators=160, min_samples_leaf=8, random_state=2026, n_jobs=-1
        )
        verify_model = RandomForestRegressor(
            n_estimators=160, min_samples_leaf=8, random_state=2026, n_jobs=-1
        )
        allow_completion_model = RandomForestClassifier(
            n_estimators=160, min_samples_leaf=8, random_state=2026, n_jobs=-1
        )
        verify_completion_model = RandomForestClassifier(
            n_estimators=160, min_samples_leaf=8, random_state=2026, n_jobs=-1
        )
    allow_model.fit(_matrix(allow), [float(row["observed_cost"]) for row in allow])
    verify_model.fit(_matrix(verify), [float(row["observed_cost"]) for row in verify])
    allow_completion_model.fit(_matrix(allow), [bool(row["observed_completed"]) for row in allow])
    verify_completion_model.fit(_matrix(verify), [bool(row["observed_completed"]) for row in verify])
    return TLearner(
        allow_model=allow_model,
        verify_model=verify_model,
        allow_completion_model=allow_completion_model,
        verify_completion_model=verify_completion_model,
    )
