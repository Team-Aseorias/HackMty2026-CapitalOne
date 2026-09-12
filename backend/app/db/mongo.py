from __future__ import annotations

from typing import Any

from app.core.config import settings

PURCHASE_ATTEMPTS = "purchase_attempts"
DECISIONS = "decisions"
OUTCOMES = "outcomes"
SIM_RUNS = "simulation_runs"
SIM_RESULTS = "simulation_results"

_client: Any | None = None


def is_configured() -> bool:
    return bool(settings.mongo_uri)


def get_client() -> Any:
    """Return the shared async client or fail clearly when Mongo is disabled."""
    from pymongo import AsyncMongoClient

    global _client
    if not is_configured():
        raise RuntimeError("MONGO_URI no está configurado en el entorno")
    if _client is None:
        _client = AsyncMongoClient(
            settings.mongo_uri,
            tz_aware=True,
            serverSelectionTimeoutMS=5_000,
            appname="ancla-backend",
        )
    return _client


def get_database() -> Any | None:
    """Return the database when configured, preserving the local demo fallback."""
    if not is_configured():
        return None
    return get_client()[settings.mongo_db]


def get_db() -> Any:
    """Strict accessor retained for DB repositories and smoke tests."""
    database = get_database()
    if database is None:
        raise RuntimeError("MONGO_URI no está configurado en el entorno")
    return database


async def ping() -> bool:
    if not is_configured():
        return False
    try:
        await get_client().admin.command("ping")
        return True
    except Exception:
        return False


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


async def ensure_indexes() -> None:
    """Create indexes shared by the inference and persistence features."""
    database = get_database()
    if database is None:
        return

    await database[DECISIONS].create_index("id", unique=True)
    await database[DECISIONS].create_index([("created_at", -1)])
    # Match the already-merged DB branch index definition. All new inference
    # documents include attempt_id; do not silently replace an existing index.
    await database[DECISIONS].create_index("attempt_id", unique=True)

    await database[PURCHASE_ATTEMPTS].create_index("id", unique=True)
    await database[PURCHASE_ATTEMPTS].create_index(
        [("account_id", 1), ("timestamp", -1)]
    )

    await database[OUTCOMES].create_index("id", unique=True)
    await database[OUTCOMES].create_index("decision_id", unique=True)

    await database[SIM_RUNS].create_index("id", unique=True)
    await database[SIM_RESULTS].create_index("run_id")
