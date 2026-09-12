from __future__ import annotations

import logging
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from app.db.mongo import DECISIONS, get_database, get_db
from app.core.config import settings

logger = logging.getLogger(__name__)


class PersistenceUnavailable(RuntimeError):
    pass


def _log_mongo_failure(operation: str, exc: Exception) -> None:
    """Report degraded persistence without logging documents or credentials."""
    logger.warning(
        "MongoDB %s failed; continuing with in-memory fallback (%s)",
        operation,
        type(exc).__name__,
    )
    if not settings.demo_mode:
        raise PersistenceUnavailable("Durable decision storage unavailable") from exc


class DecisionRepository:
    """Decision store backed by Mongo with an in-memory demo fallback."""

    _records: dict[str, dict] = {}

    @staticmethod
    def _collection():
        database = get_database()
        if database is None and not settings.demo_mode:
            raise PersistenceUnavailable("MongoDB is required outside demo mode")
        return database[DECISIONS] if database is not None else None

    @staticmethod
    def _clean(document: dict | None) -> dict | None:
        if document is None:
            return None
        clean_document = deepcopy(document)
        clean_document.pop("_id", None)
        # This helper is used only for documents actually read from Mongo.
        clean_document["persistence_source"] = "mongo"
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
                record["persistence_source"] = "mongo"
                await collection.replace_one(
                    {"id": record["id"]}, deepcopy(record), upsert=True
                )
                record["persistence_source"] = "mongo"
            else:
                record["persistence_source"] = "memory"
        except Exception as exc:
            # A persistence outage must not block a real-time authorization.
            _log_mongo_failure("decision write", exc)
            record["persistence_source"] = "memory"
        return deepcopy(record)

    async def get(self, decision_id: str) -> dict | None:
        try:
            collection = self._collection()
            if collection is not None:
                record = self._clean(await collection.find_one({"id": decision_id}))
                if record:
                    self._records[decision_id] = record
                    return deepcopy(record)
        except Exception as exc:
            _log_mongo_failure("decision lookup", exc)
        return deepcopy(self._records.get(decision_id))

    async def transition(self, decision_id: str, expected: str, values: dict) -> dict | None:
        """Atomically claim state before external effects; fail closed on DB errors."""
        from pymongo import ReturnDocument

        try:
            collection = self._collection()
            if collection is not None:
                record = self._clean(await collection.find_one_and_update(
                    {"id": decision_id, "outcome": expected},
                    {"$set": deepcopy(values)}, return_document=ReturnDocument.AFTER,
                ))
                if record is not None:
                    self._records[decision_id] = record
                return record
        except Exception as exc:
            logger.warning("Decision transition failed (%s)", type(exc).__name__)
            raise PersistenceUnavailable("Could not confirm decision transition") from exc
        # No await between check and assignment: atomic within the demo event loop.
        record = self._records.get(decision_id)
        if record is None or record.get("outcome") != expected:
            return None
        record.update(deepcopy(values))
        return deepcopy(record)

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

    async def metrics(self) -> dict:
        try:
            collection = self._collection()
            if collection is not None:
                group = {"_id": None, "attempts": {"$sum": 1}}
                action = {"$ifNull": ["$action", "$decision"]}
                for key, field, expected in [
                    ("allowed", action, "allow"), ("verified", action, "verify"),
                    ("completed", "$outcome", "completed"),
                    ("abandoned", "$outcome", "abandoned"),
                    ("blocked", "$outcome", "blocked"),
                ]:
                    group[key] = {"$sum": {"$cond": [{"$eq": [field, expected]}, 1, 0]}}
                group["average_expected_cost"] = {"$avg": {"$cond": [
                    {"$eq": [action, "verify"]}, "$estimated_cost_verify", "$estimated_cost_allow",
                ]}}
                cursor = await collection.aggregate([{"$group": group}])
                results = [item async for item in cursor]
                result = results[0] if results else {"attempts": 0}
                result.pop("_id", None)
                result["source"] = "mongo"
                total = result["attempts"]
                result["verification_rate"] = result.get("verified", 0) / total if total else 0
                result["pending"] = total - sum(result.get(k, 0) for k in ("completed", "abandoned", "blocked"))
                return result
        except Exception as exc:
            _log_mongo_failure("metrics query", exc)
        records = list(self._records.values())
        verified = sum(row.get("action", row.get("decision")) == "verify" for row in records)
        costs = [row.get("estimated_cost_verify" if row.get("action", row.get("decision")) == "verify"
                         else "estimated_cost_allow") for row in records]
        costs = [value for value in costs if value is not None]
        result = {
            "attempts": len(records), "allowed": sum(row.get("action", row.get("decision")) == "allow" for row in records),
            "verified": verified, "verification_rate": verified / len(records) if records else 0,
            "average_expected_cost": sum(costs) / len(costs) if costs else None, "source": "memory",
        }
        result.update({state: sum(row.get("outcome") == state for row in records)
                       for state in ("completed", "abandoned", "blocked")})
        result["pending"] = len(records) - sum(result[k] for k in ("completed", "abandoned", "blocked"))
        return result

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
                    .sort("completed_at", -1)
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
                    .sort("created_at", -1)
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
