import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.repositories import decision_repository
from app.routers.demo_profiles import create_demo_profile_attempt, list_demo_profiles
from app.schemas.demo_profile import DemoPurchaseAttemptIn


def test_controlled_profiles_isolate_and_apply_abandonment_history(monkeypatch):
    monkeypatch.setattr(decision_repository.DecisionRepository, "_records", {})
    monkeypatch.setattr(decision_repository, "settings", SimpleNamespace(demo_mode=True))
    monkeypatch.setattr(decision_repository, "get_database", lambda: None)

    async def scenario():
        profiles = await list_demo_profiles()
        assert [(item.key, item.resolved_verifications, item.reported_abandons) for item in profiles] == [
            ("estable", 8, 0), ("mixto", 8, 3), ("friccion", 8, 6),
        ]
        assert "customer_id" not in profiles[0].model_dump()
        assert "account_id" not in profiles[0].model_dump()

        payload = DemoPurchaseAttemptIn(merchant="Farmacias Demo", amount=600)
        stable = await create_demo_profile_attempt("estable", payload)
        friction = await create_demo_profile_attempt("friccion", payload)

        assert stable.demo_profile_key == "estable"
        assert friction.demo_profile_key == "friccion"
        assert stable.personalization_evidence.resolved_verifications == 8
        assert stable.personalization_evidence.reported_abandons == 0
        assert friction.personalization_evidence.resolved_verifications == 8
        assert friction.personalization_evidence.reported_abandons == 6
        assert friction.risk_score == pytest.approx(stable.risk_score, abs=1e-8)
        assert friction.estimated_cost_allow == pytest.approx(stable.estimated_cost_allow, abs=1e-8)
        assert friction.estimated_cost_verify > stable.estimated_cost_verify

        updated = await decision_repository.DecisionRepository().transition(
            friction.id,
            "pending",
            {"outcome": "abandoned", "abandoned_at": datetime.now(timezone.utc).isoformat()},
        )
        assert updated is not None
        refreshed = {item.key: item for item in await list_demo_profiles()}
        assert refreshed["friccion"].resolved_verifications == 9
        assert refreshed["friccion"].reported_abandons == 7

    asyncio.run(scenario())


def test_unknown_demo_profile_is_not_resolved(monkeypatch):
    monkeypatch.setattr(decision_repository.DecisionRepository, "_records", {})
    with pytest.raises(Exception) as error:
        asyncio.run(create_demo_profile_attempt(
            "desconocido", DemoPurchaseAttemptIn(merchant="Shop", amount=10),
        ))
    assert getattr(error.value, "status_code", None) == 404
