from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

from app.ml.simulator import FEATURE_NAMES, generate_synthetic_data


def _fallback_probability(features: dict) -> float:
    value = (
        -4.4 + 2.0 * float(features.get("merchant_novelty", 0))
        + 0.0012 * float(features.get("amount", 0))
        + 0.016 * float(features.get("distance_from_usual", 0))
        + (0.7 if float(features.get("hour", 12)) < 6 else 0)
    )
    return 1 / (1 + math.exp(-max(-30, min(30, value))))


@lru_cache(maxsize=1)
def _risk_model() -> Any | None:
    try:
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.ensemble import RandomForestClassifier
    except ImportError:
        return None
    records = generate_synthetic_data(rows=2_000)
    x = [[float(row[name]) for name in FEATURE_NAMES] for row in records]
    y = [bool(row["fraud"]) for row in records]
    return CalibratedClassifierCV(
        RandomForestClassifier(n_estimators=160, min_samples_leaf=8, random_state=2026, n_jobs=-1),
        method="sigmoid",
        cv=3,
    ).fit(x, y)


class RiskService:
    def score(self, features: dict) -> float:
        """Calibrated P(fraud | pre-decision context), with a local fallback."""
        model = _risk_model()
        if model is None:
            return _fallback_probability(features)
        x = [[float(features.get(name, 0.0)) for name in FEATURE_NAMES]]
        return float(model.predict_proba(x)[0][1])
