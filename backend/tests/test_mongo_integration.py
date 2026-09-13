import asyncio
import logging
from types import SimpleNamespace

import pytest

from app.db import mongo
from app.main import app
from app.repositories import decision_repository


def test_database_is_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mongo,
        "settings",
        SimpleNamespace(mongo_uri="", mongo_db="ancla"),
    )
    monkeypatch.setattr(mongo, "_client", None)

    assert mongo.get_database() is None
    assert asyncio.run(mongo.ping()) is False
    with pytest.raises(RuntimeError, match="MONGO_URI"):
        mongo.get_db()


def test_application_keeps_inference_routes() -> None:
    paths = app.openapi()["paths"]

    assert "/purchase-attempts" in paths
    assert "/decisions/{decision_id}/complete" in paths
    assert "/evaluations/run" in paths
    assert "/health" in paths


def test_decision_write_failure_is_logged_and_falls_back(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class FailingCollection:
        async def replace_one(self, *_: object, **__: object) -> None:
            raise RuntimeError("simulated outage")

    monkeypatch.setattr(
        decision_repository,
        "get_database",
        lambda: {mongo.DECISIONS: FailingCollection()},
    )
    record_id = "logging-fallback-test"
    decision_repository.DecisionRepository._records.pop(record_id, None)
    caplog.set_level(logging.WARNING)

    saved = asyncio.run(
        decision_repository.DecisionRepository().save({"id": record_id})
    )

    assert saved["id"] == record_id
    assert "MongoDB decision write failed" in caplog.text
    decision_repository.DecisionRepository._records.pop(record_id, None)
