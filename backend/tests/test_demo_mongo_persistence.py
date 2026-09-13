"""Exercise demo feedback with the same unique attempt-ID constraint as Atlas."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest
from pymongo.errors import DuplicateKeyError

from app.repositories import decision_repository
from app.repositories.decision_repository import DecisionRepository, PersistenceUnavailable
from app.routers import decisions
from app.routers.demo_profiles import create_demo_profile_attempt
from app.schemas.decision import ActivityEvidence
from app.schemas.demo_profile import DemoPurchaseAttemptIn


class IndexedCollection:
    def __init__(self):
        self.rows = {}

    async def replace_one(self, query, doc, **kwargs):
        for row in self.rows.values():
            if row["id"] != doc["id"] and row.get("attempt_id") == doc.get("attempt_id"):
                raise DuplicateKeyError("duplicate attempt_id")
        self.rows[doc["id"]] = deepcopy(doc)

    async def find_one(self, query):
        return deepcopy(self.rows.get(query["id"]))

    async def find_one_and_update(self, query, update, **kwargs):
        row = self.rows.get(query["id"])
        if row is None or row["outcome"] != query["outcome"]:
            return None
        row.update(deepcopy(update["$set"]))
        return deepcopy(row)


@pytest.fixture
def collection(monkeypatch):
    coll = IndexedCollection()
    monkeypatch.setattr(DecisionRepository, "_records", {})
    monkeypatch.setattr(decision_repository, "get_database", lambda: {"decisions": coll})
    monkeypatch.setattr(decision_repository, "settings", SimpleNamespace(demo_mode=True))
    monkeypatch.setattr(decisions, "is_configured", lambda: False)

    async def history(*args):
        return []

    async def activity(*args):
        return ActivityEvidence(window_seconds=600, prior_attempts=0, prior_verify_abandons=0)

    monkeypatch.setattr(DecisionRepository, "history_for_account", history)
    monkeypatch.setattr(DecisionRepository, "decision_history_for_account", history)
    monkeypatch.setattr(DecisionRepository, "activity_for_account", activity)
    return coll


def test_multiple_demo_attempts_persist_and_accept_feedback(collection):
    async def scenario():
        # An existing legacy document without attempt_id must not block new ones.
        collection.rows["legacy"] = {"id": "legacy", "outcome": "completed"}
        payload = DemoPurchaseAttemptIn(merchant="Farmacias Demo", amount=90)
        first = await create_demo_profile_attempt("friccion", payload)
        second = await create_demo_profile_attempt("friccion", payload)
        assert first.persistence_source == second.persistence_source == "mongo"
        assert collection.rows[first.id]["attempt_id"] != collection.rows[second.id]["attempt_id"]
        # Read from durable storage after dropping the memory cache.
        DecisionRepository._records.clear()
        assert (await decisions.complete_decision(first.id))["outcome"] == "completed"
        assert (await decisions.abandon_decision(second.id))["outcome"] == "abandoned"
        assert collection.rows[first.id]["outcome"] == "completed"
        assert collection.rows[second.id]["outcome"] == "abandoned"
        assert (await decisions.complete_decision(first.id))["outcome"] == "completed"
        with pytest.raises(Exception) as error:
            await decisions.abandon_decision(first.id)
        assert error.value.status_code == 409

    asyncio.run(scenario())


def test_memory_only_decision_does_not_claim_outcome_conflict(collection):
    DecisionRepository._records["unsaved"] = {"id": "unsaved", "outcome": "pending"}
    with pytest.raises(PersistenceUnavailable, match="no está guardada en MongoDB"):
        asyncio.run(decisions.complete_decision("unsaved"))
    assert DecisionRepository._records["unsaved"]["outcome"] == "pending"


def test_explicit_attempt_id_is_preserved(collection):
    saved = asyncio.run(DecisionRepository().save({"attempt_id": "original-attempt", "outcome": "pending"}))
    assert saved["attempt_id"] == "original-attempt"
    assert collection.rows[saved["id"]]["attempt_id"] == "original-attempt"
