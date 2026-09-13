"""Thin async gateway for Capital One's Nessie hackathon API."""

from __future__ import annotations

from typing import Any

from app.core.config import settings


class NessieError(RuntimeError):
    pass


class NessieNotConfigured(NessieError):
    pass


class NessieRepository:
    """Read decision context through endpoints in Nessie's current OpenAPI.

    Nessie uses an API key query parameter. This adapter intentionally avoids
    legacy purchase-list and purchase-create routes that are not documented by
    the current provider contract.
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key if api_key is not None else settings.nessie_api_key
        self.base_url = (base_url or settings.nessie_base_url).rstrip("/")

    @property
    def is_configured(self) -> bool:
        """Whether this instance can create or query remote Nessie resources."""
        return bool(self.api_key)

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    async def _request(self, method: str, path: str, json: dict | None = None) -> Any:
        if not self.api_key:
            raise NessieNotConfigured("NESSIE_API_KEY is not configured")
        try:
            import httpx
        except ImportError as exc:
            raise NessieError("Install httpx to call Nessie") from exc
        try:
            async with httpx.AsyncClient(timeout=settings.nessie_timeout_seconds) as client:
                response = await client.request(
                    method, self._url(path), params={"key": self.api_key}, json=json
                )
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPError as exc:
            # HTTP exception strings may contain the API key query parameter.
            raise NessieError(f"Nessie {method} failed ({type(exc).__name__})") from exc
        except ValueError as exc:
            raise NessieError("Nessie returned invalid JSON") from exc

    async def get_account(self, account_id: str) -> dict:
        return await self._request("GET", f"accounts/{account_id}")

    async def get_customer_for_account(self, account_id: str) -> dict:
        return await self._request("GET", f"accounts/{account_id}/customer")

    async def get_merchant(self, merchant_id: str) -> dict:
        return await self._request("GET", f"merchants/{merchant_id}")

    async def context_for_account(self, account_id: str) -> tuple[dict, list[dict]]:
        """Compatibility contract: current Nessie exposes no purchase listing."""
        return await self.get_account(account_id), []

    async def context_for_attempt(
        self, account_id: str, merchant_id: str | None = None
    ) -> tuple[dict, dict, dict | None]:
        """Fetch only documented, read-only resources used before inference."""
        import asyncio

        calls = [self.get_account(account_id), self.get_customer_for_account(account_id)]
        if merchant_id:
            calls.append(self.get_merchant(merchant_id))
        values = await asyncio.gather(*calls)
        return values[0], values[1], values[2] if merchant_id else None

    async def get_purchase(self, purchase_id: str) -> dict:
        """Read a known purchase ID through the documented singular route."""
        return await self._request("GET", f"purchase/{purchase_id}")
