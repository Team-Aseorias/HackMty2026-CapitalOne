from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from app.db.mongo import get_database


class DecisionRepository:
    """Async decision store backed by Atlas when ``MONGODB_URI`` is present.

    It deliberately stores attempts separately from Nessie purchases.  Replace
    only the in-memory fallback in local demos; its contract keeps the router
    and causal logging code unchanged.
    """

    _records: dict[str, dict] = {}

    @staticmethod
    async def _collection():
        database = get_database()
        return database["decisions"] if database is not None else None

    @staticmethod
    def _clean(document: dict | None) -> dict | None:
        if document is None:
            return None
        document.pop("_id", None)
        return document

    async def save(self, decision: dict) -> dict:
        record = deepcopy(decision)
        if not record.get("id"):
            record["id"] = str(uuid4())
        record.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        self._records[record["id"]] = record
        try:
            collection = await self._collection()
            if collection is not None:
                await collection.replace_one({"id": record["id"]}, deepcopy(record), upsert=True)
        except Exception:
            # Atlas is an enhancement for persistence, never a reason to stop
            # an authorization decision in the demo.
            pass
        return deepcopy(record)

    async def get(self, decision_id: str) -> dict | None:
        record = self._records.get(decision_id)
        if record:
            return deepcopy(record)
        try:
            collection = await self._collection()
            if collection is not None:
                record = self._clean(await collection.find_one({"id": decision_id}))
                if record:
                    self._records[decision_id] = record
                    return deepcopy(record)
        except Exception:
            pass
        return None

    async def update(self, decision_id: str, values: dict) -> dict | None:
        if decision_id not in self._records:
            existing = await self.get(decision_id)
            if existing is None:
                return None
        self._records[decision_id].update(deepcopy(values))
        record = self._records[decision_id]
        try:
            collection = await self._collection()
            if collection is not None:
                await collection.update_one({"id": decision_id}, {"$set": deepcopy(values)})
        except Exception:
            pass
        return deepcopy(record)

    async def recent(self, limit: int = 25) -> list[dict]:
        try:
            collection = await self._collection()
            if collection is not None:
                records = [self._clean(item) async for item in collection.find().sort("created_at", -1).limit(limit)]
                return [record for record in records if record is not None]
        except Exception:
            pass
        return [deepcopy(record) for record in list(self._records.values())[-limit:]][::-1]

    async def history_for_account(self, account_id: str, limit: int = 20) -> list[dict]:
        try:
            collection = await self._collection()
            if collection is not None:
                records = [
                    self._clean(item) async for item in collection.find({
                        "account_id": account_id,
                        "outcome": "completed",
                    }).sort("completed_at", 1).limit(limit)
                ]
                return [record for record in records if record is not None]
        except Exception:
            pass
        records = [
            record for record in self._records.values()
            if record.get("account_id") == account_id and record.get("outcome") == "completed"
        ]
        return [deepcopy(record) for record in records[-limit:]]

    async def decision_history_for_account(self, account_id: str, limit: int = 50) -> list[dict]:
        """Return resolved local treatment outcomes for personalization."""
        try:
            collection = await self._collection()
            if collection is not None:
                records = [
                    self._clean(item) async for item in collection.find({
                        "account_id": account_id,
                        "outcome": {"$in": ["completed", "abandoned"]},
                    }).sort("created_at", 1).limit(limit)
                ]
                return [record for record in records if record is not None]
        except Exception:
            pass
        records = [
            record for record in self._records.values()
            if record.get("account_id") == account_id
            and record.get("outcome") in {"completed", "abandoned"}
        ]
        return [deepcopy(record) for record in records[-limit:]]
