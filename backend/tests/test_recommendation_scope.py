"""ANCLA recommends actions and consumes feedback; it does not move money."""
import asyncio
from types import SimpleNamespace

import httpx
import pytest

from app.core.security import require_api_key
from app.main import app
from app.repositories import decision_repository
from app.routers import decisions
from app.services.decision_service import DecisionService
from app.services.risk_service import RiskService


def test_high_abandonment_cannot_override_high_risk():
    result = DecisionService().decide(
        risk_score=0.9, expected_costs=(1, 100),
        completion_probabilities=(1, 0.1), amount=100,
    )
    assert result.decision == "verify"
    assert result.safety_override


def test_low_risk_friction_changes_recommendation():
    service = DecisionService()
    unaffected = service.decide(0.05, expected_costs=(6, 5), amount=100)
    abandonment_prone = service.decide(0.05, expected_costs=(6, 8), amount=100)
    assert unaffected.decision == "verify"
    assert abandonment_prone.decision == "allow"


def test_abandonment_history_does_not_change_fraud_score():
    features = {"amount": 50, "hour": 12, "merchant_novelty": 0}
    model = RiskService()
    assert model.score(features) == model.score({
        **features, "prior_verifications": 12, "prior_verify_abandonment_rate": 0.9,
    })


@pytest.mark.parametrize("action", ["allow", "verify"])
def test_completion_is_only_feedback(monkeypatch, action):
    repository = decision_repository.DecisionRepository
    monkeypatch.setattr(repository, "_records", {})
    monkeypatch.setattr(decision_repository, "settings", SimpleNamespace(demo_mode=True))
    monkeypatch.setattr(decision_repository, "get_database", lambda: None)
    monkeypatch.setattr(decisions, "is_configured", lambda: False)
    monkeypatch.setitem(app.dependency_overrides, require_api_key, lambda: None)

    async def scenario():
        await repository().save({
            "id": "d1", "action": action, "outcome": "pending",
        })
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            first = await client.post("/decisions/d1/complete")
            assert first.status_code == 200
            assert first.json()["outcome"] == "completed"
            assert first.json()["outcome_source"] == "consumer_report"
            assert "purchase_source" not in first.json()
            assert "purchase_id" not in first.json()
            assert (await client.post("/decisions/d1/complete")).status_code == 200
            assert (await client.post("/decisions/d1/abandon")).status_code == 409
            assert (await client.post("/decisions/d1/verification")).status_code == 404

    asyncio.run(scenario())
