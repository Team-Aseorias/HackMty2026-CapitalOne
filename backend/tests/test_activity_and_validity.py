import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from app.core.config import settings
from app.core.security import require_api_key
from app.main import app
from app.repositories import decision_repository
from app.repositories.nessie_repository import NessieRepository
from app.routers import decisions, purchase_attempts
from app.schemas.decision import ActivityEvidence
from app.schemas.purchase_attempt import PurchaseAttemptIn
from app.services.activity_service import activity_checks, activity_from_records
from app.services.decision_service import DecisionService
from app.services.purchase_service import PurchaseService
from app.services.model_diagnostics import training_bounds


NOW = datetime(2026, 9, 12, 12, tzinfo=timezone.utc)


def test_nominal_support_includes_zero_deviation_and_generator_endpoints():
    bounds = training_bounds()
    assert bounds["amount"] == (5, 1500)
    assert bounds["distance_from_usual"][0] == 0
    assert bounds["amount_zscore"][0] == 0
    assert bounds["average_purchase_amount"] == (8, 600)


def record(identifier, seconds_ago=60, outcome="abandoned", **extra):
    return {
        "id": identifier, "account_id": "a1", "action": "verify", "outcome": outcome,
        "created_at": (NOW - timedelta(seconds=seconds_ago + 1)).isoformat(),
        "abandoned_at": (NOW - timedelta(seconds=seconds_ago)).isoformat(),
        **extra,
    }


def test_window_counts_all_attempts_and_only_known_abandon_events():
    rows = [record("pending", outcome="pending"), record("completed", outcome="completed"),
            record("abandoned"), record("allow", action="allow"),
            record("old", seconds_ago=601), record("future", seconds_ago=-60),
            record("undated", created_at=None), record("no-outcome-date", abandoned_at=None)]
    activity = activity_from_records(rows + [rows[2]], NOW)
    assert activity.prior_attempts == 5
    assert activity.prior_verify_abandons == 1
    # A recent resolution of an old attempt is also relevant.
    late = activity_from_records([record("late", created_at=(NOW - timedelta(days=1)).isoformat())], NOW)
    assert late.prior_attempts == 0
    assert late.prior_verify_abandons == 1


def test_velocity_overrides_low_cost_allow_without_inventing_fraud_risk():
    activity = ActivityEvidence(window_seconds=600, prior_attempts=4, prior_verify_abandons=3)
    result = DecisionService().decide(.01, expected_costs=(1, 8), amount=50,
                                      additional_safety_checks=activity_checks(activity))
    assert result.decision == "verify"
    assert result.cost_preferred_action == "allow"
    assert result.risk_score == .01
    assert result.fraud_status == "unknown"
    assert {c.code for c in result.safety_checks if c.triggered} == {
        "attempt_velocity", "verify_abandon_velocity",
    }


def test_spaced_abandons_do_not_trigger_burst_rule():
    activity = activity_from_records([record(str(i), seconds_ago=86400 * (i + 1)) for i in range(12)], NOW)
    result = DecisionService().decide(.01, expected_costs=(1, 8), amount=50,
                                      additional_safety_checks=activity_checks(activity))
    assert result.decision == "allow"
    assert not result.safety_override


def test_exact_loss_limit_is_explainable():
    result = DecisionService().decide(.066, expected_costs=(16.70, 18.81), amount=300)
    assert result.decision == "verify"
    assert result.cost_preferred_action == "allow"
    trigger = next(c for c in result.safety_checks if c.triggered)
    assert trigger.code == "loss_limit"
    assert trigger.observed == pytest.approx(19.8)
    assert trigger.threshold == settings.max_soft_expected_loss


def test_extrapolation_and_history_evidence_are_disclosed():
    feedback = [record(str(i), seconds_ago=86400) for i in range(20)]
    result = PurchaseService().assess_with_context(
        PurchaseAttemptIn(customer_id="c1", account_id="a1", merchant="shop", amount=5000, occurred_at=NOW),
        [], {"open_date": "2025-01-01"}, feedback,
    )
    assert "outside_training_range:amount" in result.model_warnings
    assert "outside_training_range:prior_verifications" in result.model_warnings
    assert result.personalization_evidence.resolved_verifications == 20
    assert result.personalization_evidence.reported_abandons == 20
    assert result.personalization_evidence.smoothed_abandonment_rate == 21 / 26
    assert any(c.code == "amount_outside_training" and c.triggered for c in result.safety_checks)
    assert result.fraud_status == "unknown"


def test_repository_activity_is_account_scoped(monkeypatch):
    repo = decision_repository.DecisionRepository
    monkeypatch.setattr(repo, "_records", {"one": record("one"), "two": record("two", account_id="a2")})
    monkeypatch.setattr(decision_repository, "get_database", lambda: None)
    monkeypatch.setattr(decision_repository, "settings", SimpleNamespace(demo_mode=True))
    evidence = asyncio.run(repo().activity_for_account("a1", NOW))
    assert evidence.prior_attempts == 1
    assert evidence.prior_verify_abandons == 1


def test_sequence_through_http_counts_abandons_and_pending_using_server_time(monkeypatch):
    monkeypatch.setattr(decision_repository.DecisionRepository, "_records", {})
    monkeypatch.setattr(decision_repository, "settings", SimpleNamespace(demo_mode=True))
    monkeypatch.setattr(decision_repository, "get_database", lambda: None)
    monkeypatch.setattr(purchase_attempts, "is_configured", lambda: False)
    monkeypatch.setattr(decisions, "is_configured", lambda: False)
    monkeypatch.setitem(app.dependency_overrides, require_api_key, lambda: None)

    async def context(self, account_id, merchant_id=None):
        return {"customer_id": "c1", "open_date": "2025-01-01"}, {"_id": "c1"}, None

    monkeypatch.setattr(NessieRepository, "context_for_attempt", context)

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            for n in range(5):
                response = await client.post("/purchase-attempts", json={
                    "customer_id": "c1", "account_id": "a1", "merchant": "shop", "amount": 600,
                    # Backdating cannot hide a current burst from safety checks.
                    "occurred_at": "2020-01-01T12:00:00Z",
                })
                assert response.status_code == 200, response.text
                data = response.json()
                assert data["recent_activity"]["prior_attempts"] == n
                assert data["fraud_status"] == "unknown"
                if n < 3:
                    outcome = await client.post('/decisions/' + data["id"] + '/abandon')
                    assert outcome.status_code == 200
                    assert outcome.json()["fraud_status"] == "unknown"
                else:
                    assert data["recent_activity"]["prior_verify_abandons"] == 3
                    assert any(c["code"] == "verify_abandon_velocity" and c["triggered"] for c in data["safety_checks"])
                if n == 4:
                    assert any(c["code"] == "attempt_velocity" and c["triggered"] for c in data["safety_checks"])
    asyncio.run(scenario())
