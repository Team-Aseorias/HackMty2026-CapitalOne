from copy import deepcopy
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from app.ml.history_support import bounded_history
from app.ml.simulator import generate_synthetic_data
from app.schemas.purchase_attempt import PurchaseAttemptIn
from app.services.causal_service import _default_learner
from app.services.demo_profile_service import controlled_purchase_history
from app.services.purchase_service import PurchaseService
from app.services.risk_service import RiskService


@pytest.mark.parametrize("count,rate,bounded_rate", [(14, 1 / 20, 1 / 18), (32, 29 / 38, 13 / 18), (100, .4, .4)])
def test_long_histories_match_boundary_predictions_without_mutating_evidence(count, rate, bounded_rate):
    learner = _default_learner()
    row = {**generate_synthetic_data(1, seed=7702)[0],
           "prior_verifications": count, "prior_verify_abandonment_rate": rate}
    original = deepcopy(row)
    boundary = {**row, "prior_verifications": 12, "prior_verify_abandonment_rate": bounded_rate}
    predictions = learner.predict_many([row, boundary])
    assert np.allclose(predictions[0], predictions[1], atol=1e-12, rtol=0)
    assert np.allclose(learner.expected_costs(row), predictions[0][:2], atol=1e-12, rtol=0)
    assert np.allclose(learner.completion_probabilities(row), predictions[0][2:], atol=1e-12, rtol=0)
    assert RiskService().score(row) == RiskService().score(boundary)
    assert row == original


def test_training_histories_are_unchanged():
    for row in generate_synthetic_data(1000, seed=7703):
        assert bounded_history(row) == row


@pytest.mark.parametrize("field,value", [
    ("prior_verifications", float("inf")), ("prior_verifications", float("nan")),
    ("prior_verify_abandonment_rate", float("nan")),
    ("prior_verify_abandonment_rate", float("inf")),
])
def test_cap_does_not_hide_invalid_inputs(field, value):
    with pytest.raises(ValueError, match="History requires"):
        _default_learner().expected_costs({"amount": 100, field: value})


@pytest.mark.parametrize("count,abandons", [(14, 0), (9, 4), (32, 28)])
def test_purchase_preserves_real_history_and_reports_only_actual_extrapolation(count, abandons):
    now = datetime(2026, 9, 12, 12, tzinfo=timezone.utc)
    feedback = []
    for i in range(count):
        outcome = "abandoned" if i < abandons else "completed"
        feedback.append({
            "action": "verify", "outcome": outcome,
            "abandoned_at" if outcome == "abandoned" else "completed_at":
                (now - timedelta(days=i + 1)).isoformat(),
        })
    result = PurchaseService().assess_with_context(
        PurchaseAttemptIn(customer_id="c1", account_id="a1", merchant="Farmacias Demo",
                          amount=300, occurred_at=now),
        controlled_purchase_history(now), {"open_date": "2022-01-15"}, feedback,
    )
    evidence = result.personalization_evidence
    assert evidence.resolved_verifications == count
    assert evidence.reported_abandons == abandons
    assert evidence.smoothed_abandonment_rate == (abandons + 1) / (count + 6)
    assert evidence.model_prior_verifications == min(count, 12)
    assert bool(evidence.capped_fields) == (count > 12)
    assert not any(w.startswith("outside_training_range:") for w in result.model_warnings)
    assert len(feedback) == count
