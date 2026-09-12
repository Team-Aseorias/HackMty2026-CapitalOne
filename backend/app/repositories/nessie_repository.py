"""Thin async gateway for Capital One's Nessie hackathon API."""

from __future__ import annotations

from typing import Any

from app.core.config import settings


class NessieError(RuntimeError):
    pass


class NessieNotConfigured(NessieError):
    pass


class NessieRepository:
    """Read decision context and create only authorized Nessie purchases.

    Nessie uses an API key query parameter and its legacy endpoint has the
    shape ``/data/accounts/{account_id}/purchases``.  This adapter is the only
    module that knows that external contract.
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key if api_key is not None else settings.nessie_api_key
        self.base_url = (base_url or settings.nessie_base_url).rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self.base_url}/data/{path.lstrip('/')}"

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

    async def get_purchases(self, account_id: str) -> list[dict]:
        purchases = await self._request("GET", f"accounts/{account_id}/purchases")
        return purchases if isinstance(purchases, list) else []

    async def get_merchant(self, merchant_id: str) -> dict:
        return await self._request("GET", f"merchants/{merchant_id}")

    async def context_for_account(self, account_id: str) -> tuple[dict, list[dict]]:
        # Both requests are read-only, and are intentionally made before a
        # decision; no Nessie purchase is created at this point.
        import asyncio

        account, purchases = await asyncio.gather(
            self.get_account(account_id), self.get_purchases(account_id)
        )
        return account, purchases

    async def create_purchase(self, account_id: str, payload: dict) -> dict:
        merchant_id = payload.get("merchant_id")
        if not self.api_key:
            raise NessieNotConfigured("NESSIE_API_KEY is not configured")
        if not merchant_id:
            raise NessieError("merchant_id is required to create a Nessie purchase")
        nessie_payload = {
            "merchant_id": merchant_id,
            "medium": payload.get("medium", "card"),
            "purchase_date": payload.get("purchase_date"),
            "amount": float(payload["amount"]),
            "description": payload.get("description", "ANCLA authorized purchase"),
        }
        result = await self._request("POST", f"accounts/{account_id}/purchases", nessie_payload)
        purchase = result.get("objectCreated", result) if isinstance(result, dict) else {}
        purchase_id = purchase.get("_id") or purchase.get("id")
        if not purchase_id:
            raise NessieError("Nessie did not return a purchase identifier")
        return {**purchase, "id": str(purchase_id)}
