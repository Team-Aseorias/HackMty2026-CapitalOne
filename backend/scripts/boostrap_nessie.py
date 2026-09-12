# backend/scripts/bootstrap_nessie.py
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import httpx


ADDRESS = {
    "street_number": "1",
    "street_name": "Demo",
    "city": "Monterrey",
    "state": "NL",
    "zip": "64000",
}


async def _post(c: httpx.AsyncClient, path: str, payload: dict, label: str) -> dict:
    r = await c.post(path, json=payload)
    print(f"\n[{label}] POST {path} -> {r.status_code}")
    print(f"[{label}] payload: {json.dumps(payload)}")
    if r.status_code >= 400:
        print(f"[{label}] response body: {r.text}")
        r.raise_for_status()

    data = r.json()
    # Nessie envuelve la respuesta: {code, message, objectCreated: {...}}
    created = data.get("objectCreated") or data
    print(f"[{label}] _id = {created.get('_id')}")
    return created


async def main():
    base = os.getenv("NESSIE_BASE_URL", "http://api.nessieisreal.com")
    key = os.getenv("NESSIE_API_KEY", "")
    if not key:
        print("Falta NESSIE_API_KEY en .env")
        return

    async with httpx.AsyncClient(base_url=base, params={"key": key}, timeout=20.0) as c:
        merchant = await _post(c, "/merchants", {
            "name": "Farmacias Demo",
            "category": "pharmacy",
            "address": ADDRESS,
            "geocode": {"lat": 25.6866, "lng": -100.3161},
        }, "merchant")

        customer = await _post(c, "/customers", {
            "first_name": "Rosa",
            "last_name": "Martínez",
            "address": ADDRESS,
        }, "customer")

        account = await _post(c, f"/customers/{customer['_id']}/accounts", {
            "type": "Checking",
            "nickname": "Cuenta Rosa",
            "rewards": 0,
            "balance": 5000,
        }, "account")

        print("\n=== Copia esto en tu .env ===")
        print(f"TEST_MERCHANT_ID={merchant['_id']}")
        print(f"TEST_CUSTOMER_ID={customer['_id']}")
        print(f"TEST_ACCOUNT_ID={account['_id']}")


if __name__ == "__main__":
    asyncio.run(main())