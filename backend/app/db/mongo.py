from __future__ import annotations

import os
from typing import Optional

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

PURCHASE_ATTEMPTS = "purchase_attempts"
DECISIONS = "decisions"
OUTCOMES = "outcomes"
SIM_RUNS = "simulation_runs"
SIM_RESULTS = "simulation_results"

_client: Optional[AsyncMongoClient] = None

def get_client() -> AsyncMongoClient:
    global _client
    if _client is None:
        uri = os.getenv("MONGO_URI")
        if not uri:
            raise RuntimeError("MONGO_URI no está configurado en el entorno")
        _client = AsyncMongoClient(
            uri,
            tz_aware=True,
            serverSelectionTimeoutMS=5000,
            appname="ancla-backend",
        )
    return _client


def get_db() -> AsyncDatabase:
    name = os.getenv("MONGO_DB", "ancla")
    return get_client()[name]


async def ping() -> bool:
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
    db = get_db()

    await db[DECISIONS].create_index("id", unique=True)
    await db[DECISIONS].create_index([("created_at", -1)])
    await db[DECISIONS].create_index("attempt_id", unique=True)

    await db[PURCHASE_ATTEMPTS].create_index("id", unique=True)
    await db[PURCHASE_ATTEMPTS].create_index([("account_id", 1), ("timestamp", -1)])

    await db[OUTCOMES].create_index("id", unique=True)
    await db[OUTCOMES].create_index("decision_id", unique=True)

    await db[SIM_RUNS].create_index("id", unique=True)
    await db[SIM_RESULTS].create_index("run_id")