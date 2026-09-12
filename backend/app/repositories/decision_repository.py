from __future__ import annotations

import logging
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from app.db.mongo import DECISIONS, get_database, get_db

logger = logging.getLogger(__name__)


def _log_mongo_failure(operation: str, exc: Exception) -> None:
    """Report degraded persistence without logging documents or credentials."""
    logger.warning(
        "MongoDB %s failed; continuing with in-memory fallback (%s)",
        operation,
        type(exc).__name__,
    )


class DecisionRepository:
    """Decision store backed by Mongo with an in-memory demo fallback."""

    _records: dict[str, dict] = {}

    @staticmethod
    def _collection():
        database = get_database()
        return database[DECISIONS] if database is not None else None

    @staticmethod
    def _clean(document: dict | None) -> dict | None:
        if document is None:
            return None
        clean_document = deepcopy(document)
        clean_document.pop("_id", None)
        return clean_document

    async def save(self, decision: dict) -> dict:
        record = deepcopy(decision)
        if not record.get("id"):
            record["id"] = str(uuid4())
        record.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        self._records[record["id"]] = record
        try:
            collection = self._collection()
            if collection is not None:
                await collection.replace_one(
                    {"id": record["id"]}, deepcopy(record), upsert=True
                )
        except Exception as exc:
            # A persistence outage must not block a real-time authorization.
            _log_mongo_failure("decision write", exc)
        return deepcopy(record)

    async def get(self, decision_id: str) -> dict | None:
        record = self._records.get(decision_id)
        if record:
            return deepcopy(record)
        try:
            collection = self._collection()
            if collection is not None:
                record = self._clean(await collection.find_one({"id": decision_id}))
                if record:
                    self._records[decision_id] = record
                    return deepcopy(record)
        except Exception as exc:
            _log_mongo_failure("decision lookup", exc)
        return None

    async def update(self, decision_id: str, values: dict) -> dict | None:
        if decision_id not in self._records:
            existing = await self.get(decision_id)
            if existing is None:
                return None
        self._records[decision_id].update(deepcopy(values))
        record = self._records[decision_id]
        try:
            collection = self._collection()
            if collection is not None:
                await collection.update_one(
                    {"id": decision_id}, {"$set": deepcopy(values)}
                )
        except Exception as exc:
            _log_mongo_failure("decision update", exc)
        return deepcopy(record)

    async def recent(self, limit: int = 25) -> list[dict]:
        try:
            collection = self._collection()
            if collection is not None:
                records = [
                    self._clean(item)
                    async for item in collection.find()
                    .sort("created_at", -1)
                    .limit(limit)
                ]
                return [record for record in records if record is not None]
        except Exception as exc:
            _log_mongo_failure("recent decisions query", exc)
        return [
            deepcopy(record)
            for record in list(self._records.values())[-limit:]
        ][::-1]

    async def history_for_account(
        self, account_id: str, limit: int = 20
    ) -> list[dict]:
        try:
            collection = self._collection()
            if collection is not None:
                records = [
                    self._clean(item)
                    async for item in collection.find(
                        {"account_id": account_id, "outcome": "completed"}
                    )
                    .sort("completed_at", 1)
                    .limit(limit)
                ]
                return [record for record in records if record is not None]
        except Exception as exc:
            _log_mongo_failure("account purchase history query", exc)
        records = [
            record
            for record in self._records.values()
            if record.get("account_id") == account_id
            and record.get("outcome") == "completed"
        ]
        return [deepcopy(record) for record in records[-limit:]]

    async def decision_history_for_account(
        self, account_id: str, limit: int = 50
    ) -> list[dict]:
        """Return resolved treatment outcomes used to personalize inference."""
        try:
            collection = self._collection()
            if collection is not None:
                records = [
                    self._clean(item)
                    async for item in collection.find(
                        {
                            "account_id": account_id,
                            "outcome": {"$in": ["completed", "abandoned"]},
                        }
                    )
                    .sort("created_at", 1)
                    .limit(limit)
                ]
                return [record for record in records if record is not None]
        except Exception as exc:
            _log_mongo_failure("account decision history query", exc)
        records = [
            record
            for record in self._records.values()
            if record.get("account_id") == account_id
            and record.get("outcome") in {"completed", "abandoned"}
        ]
        return [deepcopy(record) for record in records[-limit:]]


# Functional API kept for compatibility with the database PR and its scripts.
async def insert_decision(doc: dict) -> None:
    await get_db()[DECISIONS].replace_one({"id": doc["id"]}, doc, upsert=True)


async def get_decision_by_id(decision_id: str) -> dict | None:
    return await get_db()[DECISIONS].find_one({"id": decision_id}, {"_id": 0})


async def get_decision_by_attempt_id(attempt_id: str) -> dict | None:
    return await get_db()[DECISIONS].find_one(
        {"attempt_id": attempt_id}, {"_id": 0}
    )


async def list_recent_decisions(limit: int = 50) -> list[dict]:
    cursor = (
        get_db()[DECISIONS].find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    )
    return [doc async for doc in cursor]


async def list_decisions_by_action(action: str, limit: int = 100) -> list[dict]:
    """Support both the DB branch's ``action`` and inference's ``decision``."""
    cursor = (
        get_db()[DECISIONS]
        .find({"$or": [{"action": action}, {"decision": action}]}, {"_id": 0})
        .sort("created_at", -1)
        .limit(limit)
    )
    return [doc async for doc in cursor]
