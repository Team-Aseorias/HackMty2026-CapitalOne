"""Offline HTTP flow with actual inference and simulated provider context."""
import asyncio
from types import SimpleNamespace

import httpx
import pytest

from app.core.security import require_api_key
from app.main import app
from app.repositories import decision_repository
from app.repositories.nessie_repository import NessieRepository, NessieError
from app.routers import decisions, purchase_attempts


@pytest.mark.parametrize("provider_available", [True, False])
def test_inference_feedback_and_metrics_without_external_writes(monkeypatch, provider_available):
    repository = decision_repository.DecisionRepository
    monkeypatch.setattr(repository, "_records", {})
    monkeypatch.setattr(decision_repository, "settings", SimpleNamespace(demo_mode=True))
    monkeypatch.setattr(decision_repository, "get_database", lambda: None)
    monkeypatch.setattr(purchase_attempts, "is_configured", lambda: False)
    monkeypatch.setattr(decisions, "is_configured", lambda: False)
    monkeypatch.setitem(app.dependency_overrides, require_api_key, lambda: None)

    async def context(self, account_id, merchant_id=None):
        if not provider_available:
            raise NessieError("Simulated outage")
        return (
            {"customer_id": "c1", "open_date": "2025-01-01"},
            {"_id": "c1"},
            {"_id": merchant_id} if merchant_id else None,
        )

    monkeypatch.setattr(NessieRepository, "context_for_attempt", context)

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/purchase-attempts", json={
                "customer_id": "c1", "account_id": "a1", "merchant": "shop", "amount": 20,
                "occurred_at": "2026-09-12T12:00:00Z",
            })
            assert response.status_code == 200, response.text
            result = response.json()
            assert result["decision"] in {"allow", "verify"}
            assert result["model_version"] == "synthetic-v3"
            assert result["persistence_source"] == "memory"
            if not provider_available:
                assert result["decision"] == "verify"
                assert result["safety_override"]
            outcome = await client.post(f'/decisions/{result["id"]}/abandon')
            assert outcome.status_code == 200
            metrics = (await client.get("/dashboard/metrics")).json()
            assert metrics["attempts"] == 1
            assert metrics["abandoned"] == 1
            assert metrics["allowed"] + metrics["verified"] == 1

    asyncio.run(scenario())
