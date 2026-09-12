from __future__ import annotations

from app.db.mongo import get_db, DECISIONS


async def insert_decision(doc: dict) -> None:
    """Inserta una decisión de ANCLA."""
    await get_db()[DECISIONS].insert_one(doc)


async def get_decision_by_id(decision_id: str) -> dict | None:
    return await get_db()[DECISIONS].find_one({"id": decision_id}, {"_id": 0})


async def get_decision_by_attempt_id(attempt_id: str) -> dict | None:
    return await get_db()[DECISIONS].find_one({"attempt_id": attempt_id}, {"_id": 0})


async def list_recent_decisions(limit: int = 50) -> list[dict]:
    cursor = (
        get_db()[DECISIONS]
        .find({}, {"_id": 0})
        .sort("created_at", -1)
        .limit(limit)
    )
    return [doc async for doc in cursor]


async def list_decisions_by_action(action: str, limit: int = 100) -> list[dict]:
    """Filtra por acción ('allow' o 'verify'). Útil para métricas de operación."""
    cursor = (
        get_db()[DECISIONS]
        .find({"action": action}, {"_id": 0})
        .sort("created_at", -1)
        .limit(limit)
    )
    return [doc async for doc in cursor]