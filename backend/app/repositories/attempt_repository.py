# app/db/attempt_repository.py
from __future__ import annotations

from app.db.mongo import get_db, PURCHASE_ATTEMPTS


async def insert_attempt(doc: dict) -> None:
    """Inserta un intento crudo de compra."""
    await get_db()[PURCHASE_ATTEMPTS].insert_one(doc)


async def get_attempt_by_id(attempt_id: str) -> dict | None:
    return await get_db()[PURCHASE_ATTEMPTS].find_one(
        {"id": attempt_id}, {"_id": 0}
    )


async def list_recent_attempts(account_id: str, limit: int = 20) -> list[dict]:
    cursor = (
        get_db()[PURCHASE_ATTEMPTS]
        .find({"account_id": account_id}, {"_id": 0})
        .sort("timestamp", -1)
        .limit(limit)
    )
    return [doc async for doc in cursor]


async def count_attempts_since(account_id: str, since_iso: str) -> int:
    """Cuenta intentos de una cuenta desde un timestamp ISO. Útil para velocity."""
    return await get_db()[PURCHASE_ATTEMPTS].count_documents(
        {"account_id": account_id, "timestamp": {"$gte": since_iso}}
    )