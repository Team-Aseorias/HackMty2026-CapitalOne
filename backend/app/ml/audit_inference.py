"""Reproducible, offline audit. Prints JSON; never contacts MongoDB or Nessie."""
from __future__ import annotations

import json
from statistics import mean
from time import perf_counter

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from app.ml.simulator import FEATURE_NAMES, generate_synthetic_data
from app.services.causal_service import _default_learner
from app.services.risk_service import RiskService
from app.services.decision_service import DecisionService
from app.services.evaluation_service import EvaluationService


def probability_metrics(target, prediction) -> dict:
    y, p = np.asarray(target, dtype=int), np.asarray(prediction, dtype=float)
    bins = []
    for lower in np.arange(0, 1, 0.1):
        mask = (p >= lower) & (p < lower + .1 if lower < .9 else p <= 1)
        if mask.any():
            bins.append({"n": int(mask.sum()), "predicted": float(p[mask].mean()),
                         "observed": float(y[mask].mean())})
    return {
        "n": len(y), "prevalence": float(y.mean()),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "roc_auc": float(roc_auc_score(y, p)) if len(set(y)) > 1 else None,
        "pr_auc": float(average_precision_score(y, p)) if y.any() else None,
        "ece_10_bins": sum(b["n"] * abs(b["predicted"] - b["observed"]) for b in bins) / len(y),
        "reliability_bins": bins,
    }


def audit(seeds=(3101, 3102, 3103), rows=3000) -> dict:
    started = perf_counter()
    learner = _default_learner()
    risk_model = RiskService()
    results = []
    for seed in seeds:
        records = generate_synthetic_data(rows=rows, seed=seed)
        features = [{name: row[name] for name in FEATURE_NAMES} for row in records]
        risks = risk_model.scores(features)
        predictions = learner.predict_many(features)
        genuine_verify = [i for i, row in enumerate(records) if not row["fraud"] and row["treatment"] == "verify"]
        result = {
            "seed": seed, "fraud": probability_metrics([row["fraud"] for row in records], risks),
            "genuine_abandonment_verify": probability_metrics(
                [not records[i]["observed_completed"] for i in genuine_verify],
                [1 - predictions[i][3] for i in genuine_verify],
            ),
            "policies": [policy.model_dump() for policy in EvaluationService().run(rows, seed)],
        }
        # Paired counterfactual inputs: same transaction, same risk, different
        # histories. This is a behavioral invariant, not an observed causal proof.
        low = [{**row, "prior_verifications": 12, "prior_verify_abandonment_rate": 1/18} for row in features]
        high = [{**row, "prior_verifications": 12, "prior_verify_abandonment_rate": 13/18} for row in features]
        low_p, high_p = learner.predict_many(low), learner.predict_many(high)
        changes = reverse_changes = 0
        for row, risk, lp, hp in zip(features, risks, low_p, high_p):
            a = DecisionService().decide(risk, expected_costs=lp[:2], amount=row["amount"]).decision
            b = DecisionService().decide(risk, expected_costs=hp[:2], amount=row["amount"]).decision
            changes += a == "verify" and b == "allow"
            reverse_changes += a == "allow" and b == "verify"
        result["paired_histories"] = {
            "verify_to_allow": changes, "allow_to_verify": reverse_changes,
            "monotonicity_violations": sum(h[3] > l[3] + 1e-12 for l, h in zip(low_p, high_p)),
        }
        # Predictions at the sensitive subgroup separately (not just averages).
        sensitive = [i for i in genuine_verify if records[i]["prior_verify_abandonment_rate"] >= .3]
        if sensitive:
            result["sensitive_subgroup"] = probability_metrics(
                [not records[i]["observed_completed"] for i in sensitive],
                [1 - predictions[i][3] for i in sensitive],
            )
        results.append(result)
    return {"source": "synthetic randomized simulator; not real-world validation",
            "training_seed": 2026, "seeds": results,
            "mean_fraud_brier": mean(r["fraud"]["brier"] for r in results),
            "mean_abandonment_brier": mean(r["genuine_abandonment_verify"]["brier"] for r in results),
            "elapsed_seconds": perf_counter() - started}


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, allow_nan=False))
