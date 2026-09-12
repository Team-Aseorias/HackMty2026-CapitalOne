"""Robustness, model isolation, leakage and numerical-policy regression tests."""
from copy import deepcopy

import numpy as np
import pytest

from app.core.config import settings
from app.ml.probability_models import RegularizedProbabilityModel
from app.ml.simulator import FEATURE_NAMES, generate_synthetic_data
from app.ml.train_causal import fit_t_learner
from app.services.causal_service import _default_learner
from app.services.decision_service import DecisionService
from app.services.feature_service import FeatureService
from app.services.risk_service import RiskService


@pytest.mark.parametrize("amount", [1, 50, 499, 500, 1000000])
def test_inference_is_finite_and_batch_matches_single(amount):
    features = {"amount": amount, "hour": 12, "merchant_novelty": 0}
    learner = _default_learner()
    prediction = learner.predict_many([features])[0]
    assert np.isfinite(prediction).all()
    assert min(prediction[:2]) >= 0
    assert all(0 <= p <= 1 for p in prediction[2:])
    assert learner.expected_costs(features) == prediction[:2]
    assert learner.completion_probabilities(features) == prediction[2:]


def test_personalization_monotone_across_many_contexts():
    learner = _default_learner()
    records = generate_synthetic_data(100, seed=7701)
    for row in records:
        rates = [0.05, .2, .4, .7, .95]
        profiles = [{**row, "prior_verifications": 12, "prior_verify_abandonment_rate": rate} for rate in rates]
        outcomes = learner.predict_many(profiles)
        assert all(a[3] >= b[3] for a, b in zip(outcomes, outcomes[1:]))
        assert all(a[1] <= b[1] for a, b in zip(outcomes, outcomes[1:]))
        # BLAS vectorized reductions may differ in the last floating-point bit.
        assert np.ptp(RiskService().scores(profiles)) < 1e-12
        assert np.ptp([o[0] for o in outcomes]) < 1e-10


@pytest.mark.parametrize("count", [0, 1, 2])
def test_insufficient_history_does_not_personalize(count):
    baseline = {"amount": 100, "hour": 12, "prior_verifications": count}
    low = {**baseline, "prior_verify_abandonment_rate": .01}
    high = {**baseline, "prior_verify_abandonment_rate": .99}
    assert _default_learner().predict_many([low]) == _default_learner().predict_many([high])


@pytest.mark.parametrize("risk,amount,context", [
    (settings.max_soft_risk, 1, True),
    (.1, settings.max_soft_expected_loss / .1, True),
    (.001, settings.max_soft_amount, True),
    (.001, 1, False),
])
def test_safety_limits_always_override_friction(risk, amount, context):
    result = DecisionService().decide(risk, expected_costs=(0, 10000),
                                     amount=amount, context_available=context)
    assert result.decision == "verify"
    assert result.safety_override


@pytest.mark.parametrize("risk", [float("nan"), float("inf"), -.01, 1.01])
def test_invalid_risk_is_rejected(risk):
    with pytest.raises(ValueError):
        DecisionService().decide(risk, expected_costs=(1, 2), amount=10)


@pytest.mark.parametrize("amount", [float("nan"), float("inf"), -1])
def test_invalid_amount_is_rejected(amount):
    with pytest.raises(ValueError):
        DecisionService().decide(.1, expected_costs=(1, 2), amount=amount)


@pytest.mark.parametrize("costs", [(float("nan"), 1), (1, float("inf")), (-1, 2), (1,)])
def test_invalid_costs_are_rejected(costs):
    with pytest.raises(ValueError):
        DecisionService().decide(.1, expected_costs=costs, amount=10)


def test_nan_features_are_rejected_by_model():
    with pytest.raises(ValueError):
        RiskService().score({"amount": float("nan")})


def test_empty_batch_and_single_class_are_supported():
    assert RiskService().scores([]) == []
    assert _default_learner().predict_many([]) == []
    model = RegularizedProbabilityModel().fit([[0], [1], [2]], [0, 0, 0])
    probabilities = model.predict_proba([[0], [100]])
    assert 0 < probabilities[0][1] < 1
    assert np.array_equal(probabilities[0], probabilities[1])


def test_oracle_and_unassigned_outcome_fields_do_not_affect_training():
    rows = generate_synthetic_data(800, seed=7201)
    modified = deepcopy(rows)
    for row in modified:
        for field in ("cost_allow", "cost_verify", "completed_allow", "completed_verify",
                      "fraud_loss_allow", "fraud_loss_verify"):
            row[field] = float("nan")
    first, second = fit_t_learner(rows), fit_t_learner(modified)
    features = [{k: row[k] for k in FEATURE_NAMES} for row in rows[:10]]
    assert np.allclose(first.predict_many(features), second.predict_many(features))


def test_missing_treatment_arm_fails_with_clear_error():
    rows = generate_synthetic_data(100, seed=7202)
    with pytest.raises(ValueError, match="per arm"):
        fit_t_learner([row for row in rows if row["treatment"] == "verify"])


def test_future_pending_and_unstamped_feedback_is_excluded():
    attempt = {"amount": 10, "merchant": "shop", "occurred_at": "2026-09-12T12:00:00Z"}
    records = [
        {"action": "verify", "outcome": "abandoned", "abandoned_at": "2026-09-11T12:00:00Z"},
        {"action": "verify", "outcome": "abandoned", "abandoned_at": "2026-09-13T12:00:00Z"},
        {"action": "verify", "outcome": "pending", "created_at": "2026-09-01T12:00:00Z"},
        {"action": "verify", "outcome": "abandoned"},
    ]
    features = FeatureService().build(attempt, [], decision_history=records)
    assert features["prior_verifications"] == 1
    assert features["prior_verify_abandonment_rate"] == 1 / 6


def test_bad_history_does_not_poison_features_or_leak_future_purchases():
    attempt = {"amount": 10, "merchant": "shop", "occurred_at": "2026-09-12T12:00:00Z"}
    history = [
        {"amount": 20, "merchant": "shop", "purchase_date": "2026-09-11"},
        {"amount": "NaN", "purchase_date": "2026-09-11"},
        {"amount": -100, "purchase_date": "2026-09-11"},
        {"amount": 10000, "purchase_date": "2026-09-13"},
    ]
    features = FeatureService().build(attempt, history, {"open_date": "2025-01-01"})
    assert features["recent_spend"] == 20
    assert features["recent_purchase_count"] == 1
    assert np.isfinite(list(features.values())).all()
