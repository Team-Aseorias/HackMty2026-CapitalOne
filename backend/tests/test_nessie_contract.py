"""Nessie adapter only uses resources in the current documented contract."""
import asyncio

import httpx

from app.repositories.nessie_repository import NessieRepository


def test_attempt_context_uses_documented_read_routes(monkeypatch):
    seen = []

    def handle(request):
        seen.append((request.method, request.url.path))
        assert request.url.params["key"] == "test-key"
        payloads = {
            "/accounts/account": {"_id": "account", "customer_id": "customer"},
            "/accounts/account/customer": {"_id": "customer"},
            "/merchants/merchant": {"_id": "merchant"},
            "/purchase/purchase": {"_id": "purchase", "status": "pending"},
        }
        return httpx.Response(200, json=payloads[request.url.path])

    original_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original_client(
        transport=httpx.MockTransport(handle), **kwargs,
    ))

    async def scenario():
        gateway = NessieRepository(
            api_key="test-key", base_url="https://api.nessieisreal.com/"
        )
        account, customer, merchant = await gateway.context_for_attempt("account", "merchant")
        assert account["customer_id"] == customer["_id"]
        assert merchant["_id"] == "merchant"
        assert (await gateway.get_purchase("purchase"))["status"] == "pending"

    asyncio.run(scenario())
    assert seen == [
        ("GET", "/accounts/account"),
        ("GET", "/accounts/account/customer"),
        ("GET", "/merchants/merchant"),
        ("GET", "/purchase/purchase"),
    ]


def test_account_context_does_not_call_undocumented_purchase_list(monkeypatch):
    async def get_account(_self, account_id):
        return {"_id": account_id}

    monkeypatch.setattr(NessieRepository, "get_account", get_account)
    account, history = asyncio.run(
        NessieRepository(api_key="test-key").context_for_account("account")
    )
    assert account["_id"] == "account"
    assert history == []
    assert not hasattr(NessieRepository, "get_purchases")
    assert not hasattr(NessieRepository, "create_purchase")
