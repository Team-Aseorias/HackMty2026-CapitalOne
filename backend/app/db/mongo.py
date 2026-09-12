from typing import Any

from app.core.config import settings

_client: Any | None = None


def get_database() -> Any:
    """Return the async Mongo database lazily, keeping imports optional for local work."""
    from pymongo import AsyncMongoClient

    global _client
    if not settings.mongodb_uri:
        return None
    if _client is None:
        _client = AsyncMongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=1_500)
    return _client[settings.mongodb_database]
