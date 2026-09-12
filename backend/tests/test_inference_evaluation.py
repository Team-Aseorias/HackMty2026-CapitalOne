"""Independent acceptance checks for the synthetic model, not real-bank claims."""
import numpy as np

from app.ml.audit_inference import probability_metrics
from app.ml.causal_refutation import refute
from app.ml.simulator import generate_synthetic_data
from app.services.causal_service import _default_learner
from app.services.evaluation_service import EvaluationService
from app.services.risk_service import RiskService


def test_probabilities_generalize_to_unseen_synthetic_seed():
    rows = generate_synthetic_data(3000, seed=5201)
    risks = RiskService().scores(rows)
    genuine_verify = [row for row in rows if not row["fraud"] and row["treatment"] == "verify"]
    predictions = _default_learner().predict_many(genuine_verify)
    fraud = probability_metrics([row["fraud"] for row in rows], risks)
    abandonment = probability_metrics(
        [not row["observed_completed"] for row in genuine_verify], [1 - p[3] for p in predictions],
    )
    assert fraud["roc_auc"] > .65
    assert fraud["brier"] < fraud["prevalence"] * (1 - fraud["prevalence"])
    # A small tolerance acknowledges sampling uncertainty on the rare outcome.
    assert abandonment["brier"] < abandonment["prevalence"] * (1 - abandonment["prevalence"]) + .003
    assert abandonment["ece_10_bins"] < .06


def test_serving_policy_never_relaxes_safety_limits_on_unseen_data():
    reports = {result.policy: result for result in EvaluationService().run(1000, 5202)}
    assert reports["causal"].safety_violations == 0
    assert reports["causal_unpersonalized"].safety_violations == 0
    # With this simulator verification never increases realized fraud loss;
    # the serving policy verifies every case the safety-only baseline verifies.
    assert reports["causal"].fraud_loss_per_attempt <= reports["predictive"].fraud_loss_per_attempt
    for row in reports.values():
        assert np.isfinite(row.expected_cost)
        assert 0 <= row.legitimate_abandonment_rate <= 1


def test_randomized_refutations_are_consistent():
    report = refute(rows=3000, seed=5203, repetitions=100)
    assert report["bootstrap_95_ci"][0] > 0
    assert abs(report["placebo_mean_effect"]) < .01
    assert report["placebo_95_interval"][0] < 0 < report["placebo_95_interval"][1]
    assert abs(report["random_common_cause_effect"] - report["abandonment_ate_verify_minus_allow"]) < .01
