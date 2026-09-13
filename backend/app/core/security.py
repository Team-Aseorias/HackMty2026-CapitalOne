"""Server-to-server authentication; never put these keys in a public client."""

from secrets import compare_digest
from fastapi import Header, HTTPException
from app.core.config import settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not settings.api_key and settings.demo_mode:
        return
    if not settings.api_key or not compare_digest(x_api_key or "", settings.api_key):
        raise HTTPException(401, "Backend API key required")
