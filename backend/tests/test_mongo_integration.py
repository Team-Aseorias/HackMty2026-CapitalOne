import asyncio
from types import SimpleNamespace

import pytest

from app.db import mongo
from app.main import app


def test_database_is_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mongo,
        "settings",
        SimpleNamespace(mongodb_uri="", mongodb_database="ancla"),
    )
    monkeypatch.setattr(mongo, "_client", None)

    assert mongo.get_database() is None
    assert asyncio.run(mongo.ping()) is False
    with pytest.raises(RuntimeError, match="MONGODB_URI"):
        mongo.get_db()


def test_application_keeps_inference_routes() -> None:
    paths = app.openapi()["paths"]

    assert "/purchase-attempts" in paths
    assert "/decisions/{decision_id}/complete" in paths
    assert "/evaluations/run" in paths
    assert "/health" in paths
