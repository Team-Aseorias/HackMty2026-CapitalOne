from __future__ import annotations

from app.db.mongo import get_db, OUTCOMES


async def insert_outcome(doc: dict) -> None:
    """Persist a decision outcome idempotently."""
    await get_db()[OUTCOMES].replace_one(
        {"decision_id": doc["decision_id"]}, doc, upsert=True
    )


async def get_outcome_by_decision_id(decision_id: str) -> dict | None:
    return await get_db()[OUTCOMES].find_one(
        {"decision_id": decision_id}, {"_id": 0}
    )


async def list_recent_outcomes(limit: int = 50) -> list[dict]:
    cursor = (
        get_db()[OUTCOMES]
        .find({}, {"_id": 0})
        .sort("created_at", -1)
        .limit(limit)
    )
    return [doc async for doc in cursor]


async def count_by_status(status: str) -> int:
    """Cuenta outcomes por estado. Para el dashboard de operación."""
    return await get_db()[OUTCOMES].count_documents({"status": status})
