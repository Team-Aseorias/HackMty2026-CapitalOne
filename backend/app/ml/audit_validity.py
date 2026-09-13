"""Fresh-seed synthetic validation and paired policy uncertainty; prints JSON."""
import json

import numpy as np

from app.ml.audit_inference import audit
from app.ml.simulator import FEATURE_NAMES, generate_synthetic_data
from app.services.causal_service import _default_learner
from app.services.risk_service import RiskService
from app.services.decision_service import DecisionService
from app.core.config import settings


def validity(seeds=(6201, 6202, 6203), rows=3000):
    report = audit(seeds=seeds, rows=rows)
    del report["elapsed_seconds"]
    differences = []
    allowed_fraud = fraudulent = 0
    for seed in seeds:
        records = generate_synthetic_data(rows=rows, seed=seed)
        features = [{name: row[name] for name in FEATURE_NAMES} for row in records]
        predictions = _default_learner().predict_many(features)
        risks = RiskService().scores(features)
        for row, risk, prediction in zip(records, risks, predictions):
            chosen = DecisionService().decide(
                risk, expected_costs=prediction[:2], amount=row["amount"],
            ).decision
            predictive = ("verify" if (
                risk >= settings.max_soft_risk or risk * row["amount"] >= settings.max_soft_expected_loss
                or row["amount"] >= settings.max_soft_amount
            ) else "allow")
            differences.append(row["cost_" + chosen] - row["cost_" + predictive])
            fraudulent += int(row["fraud"])
            allowed_fraud += int(row["fraud"] and chosen == "allow")
    delta = np.asarray(differences)
    rng = np.random.default_rng(6204)
    boot = [float(rng.choice(delta, size=len(delta), replace=True).mean()) for _ in range(1000)]
    report["paired_causal_minus_predictive_cost"] = {
        "mean_per_attempt": float(delta.mean()),
        "bootstrap_95_interval": np.quantile(boot, [.025, .975]).tolist(),
        "bootstrap_seed": 6204,
        "bootstrap_repetitions": 1000,
        "n": len(delta),
        "interpretation": "Negative favors causal; interval is conditional on this fixed simulator and model",
    }
    report["fraud_is_not_assumed_absent"] = {
        "synthetic_fraud_cases": fraudulent,
        "synthetic_fraud_cases_recommended_allow": allowed_fraud,
        "live_feedback_fraud_labels": "unknown; completion is not legitimacy",
    }
    report["limitations"] = [
        "Independent synthetic rows do not validate serial dependence, attack detection or live individual effects.",
        "Repeated abandoned transactions have no adjudicated fraud labels; friction history is only a proxy.",
        "Training histories contain at most 12 prior verifications; larger counts are extrapolation.",
        "The simulator assumes no voluntary abandonment under allow.",
        "Velocity rule thresholds are demo policy assumptions, not learned or calibrated fraud probabilities.",
    ]
    return report


if __name__ == "__main__":
    print(json.dumps(validity(), indent=2, allow_nan=False))
