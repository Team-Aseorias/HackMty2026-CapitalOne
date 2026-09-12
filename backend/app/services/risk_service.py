"""Independent fraud prediction; abandonment history never enters this model."""
from functools import lru_cache

from app.ml.probability_models import feature_matrix, fit_fraud_model
from app.ml.simulator import generate_synthetic_data


@lru_cache(maxsize=1)
def _risk_model():
    return fit_fraud_model(generate_synthetic_data(rows=12000, seed=2026))


class RiskService:
    def score(self, features: dict) -> float:
        return self.scores([features])[0]

    def scores(self, features: list[dict]) -> list[float]:
        if not features:
            return []
        probabilities = _risk_model().predict_proba(feature_matrix(features, personalization=False))
        return [float(row[1]) for row in probabilities]
