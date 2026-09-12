# app/services/nessie_client.py
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

import httpx


# ---------- Interfaz común ----------

class NessieAdapter(Protocol):
    async def get_customer(self, customer_id: str) -> dict[str, Any]: ...
    async def get_customer_accounts(self, customer_id: str) -> list[dict[str, Any]]: ...
    async def get_merchant(self, merchant_id: str) -> dict[str, Any]: ...
    async def list_purchases(self, account_id: str) -> list[dict[str, Any]]: ...
    async def create_purchase(
        self,
        account_id: str,
        merchant_id: str,
        amount: float,
        medium: str = "balance",
        purchase_date: str | None = None,
        status: str = "completed",
    ) -> dict[str, Any]: ...
    async def ping(self) -> bool: ...
    async def close(self) -> None: ...


# ---------- Implementación HTTP real ----------

class HttpNessieClient:
    """Cliente HTTP para Nessie. Único punto de contacto con la API."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                params={"key": self._api_key},
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ---- Lectura ----

    async def get_customer(self, customer_id: str) -> dict[str, Any]:
        c = await self._http()
        r = await c.get(f"/customers/{customer_id}")
        r.raise_for_status()
        return r.json()

    async def get_customer_accounts(self, customer_id: str) -> list[dict[str, Any]]:
        """Nessie lista las cuentas por cliente, no por account_id directo."""
        c = await self._http()
        r = await c.get(f"/customers/{customer_id}/accounts")
        r.raise_for_status()
        return r.json()

    async def get_merchant(self, merchant_id: str) -> dict[str, Any]:
        c = await self._http()
        r = await c.get(f"/merchants/{merchant_id}")
        r.raise_for_status()
        return r.json()

    async def list_purchases(self, account_id: str) -> list[dict[str, Any]]:
        c = await self._http()
        r = await c.get(f"/accounts/{account_id}/purchases")
        r.raise_for_status()
        return r.json()

    # ---- Escritura ----

    async def create_purchase(
        self,
        account_id: str,
        merchant_id: str,
        amount: float,
        medium: str = "balance",
        purchase_date: str | None = None,
        status: str = "completed",
    ) -> dict[str, Any]:
        c = await self._http()
        payload = {
            "merchant_id": merchant_id,
            "medium": medium,
            "amount": amount,
            "status": status,
            "purchase_date": purchase_date or date.today().isoformat(),
        }
        r = await c.post(f"/accounts/{account_id}/purchases", json=payload)
        r.raise_for_status()
        return r.json()

    # ---- Health ----

    async def ping(self) -> bool:
        try:
            c = await self._http()
            # Endpoint barato y estable para verificar que la key funciona
            r = await c.get("/customers")
            return r.status_code < 500
        except Exception:
            return False


# ---------- Implementación local (fallback) ----------

class LocalNessieClient:
    """
    Adapter local que simula Nessie leyendo un JSON.
    Mismo contrato que HttpNessieClient.
    """

    def __init__(self, data_path: Path | None = None):
        default_path = Path(__file__).resolve().parents[2] / "data" / "nessie_fallback.json"
        self._data_path = data_path or default_path
        self._store: dict[str, Any] = {
            "accounts": {},
            "customers": {},
            "merchants": {},
            "purchases": {},
        }
        self._load()

    def _load(self) -> None:
        if self._data_path.exists():
            self._store = json.loads(self._data_path.read_text(encoding="utf-8"))

    async def close(self) -> None:
        return None

    async def ping(self) -> bool:
        return True

    async def get_customer(self, customer_id: str) -> dict[str, Any]:
        cus = self._store["customers"].get(customer_id)
        if cus is None:
            raise KeyError(f"Cliente {customer_id} no existe en fallback local")
        return cus

    async def get_customer_accounts(self, customer_id: str) -> list[dict[str, Any]]:
        return [
            a for a in self._store["accounts"].values()
            if a.get("customer_id") == customer_id
        ]

    async def get_merchant(self, merchant_id: str) -> dict[str, Any]:
        mer = self._store["merchants"].get(merchant_id)
        if mer is None:
            raise KeyError(f"Merchant {merchant_id} no existe en fallback local")
        return mer

    async def list_purchases(self, account_id: str) -> list[dict[str, Any]]:
        return [
            p for p in self._store["purchases"].values()
            if p.get("account_id") == account_id
        ]

    async def create_purchase(
        self,
        account_id: str,
        merchant_id: str,
        amount: float,
        medium: str = "balance",
        purchase_date: str | None = None,
        status: str = "completed",
    ) -> dict[str, Any]:
        pid = f"pur_{uuid4().hex[:12]}"
        record = {
            "_id": pid,
            "account_id": account_id,
            "merchant_id": merchant_id,
            "amount": amount,
            "medium": medium,
            "status": status,
            "purchase_date": purchase_date or date.today().isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._store["purchases"][pid] = record
        return record


# ---------- Factory ----------

_nessie: NessieAdapter | None = None


def get_nessie() -> NessieAdapter:
    global _nessie
    if _nessie is None:
        use_local = os.getenv("NESSIE_USE_LOCAL", "").lower() in {"1", "true", "yes"}
        if use_local:
            _nessie = LocalNessieClient()
        else:
            base_url = os.getenv("NESSIE_BASE_URL", "http://api.nessieisreal.com")
            api_key = os.getenv("NESSIE_API_KEY", "")
            if not api_key:
                _nessie = LocalNessieClient()
            else:
                _nessie = HttpNessieClient(base_url=base_url, api_key=api_key)
    return _nessie


def reset_nessie() -> None:
    global _nessie
    _nessie = None