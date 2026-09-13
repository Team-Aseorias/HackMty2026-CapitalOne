"""Opt-in live check using documented Nessie reads and ANCLA's Mongo writes."""
import argparse
import asyncio
import json

import httpx

from app.core.config import settings
from app.db.mongo import close_client, get_db
from app.main import app
from app.repositories.decision_repository import DecisionRepository
from app.repositories.nessie_repository import NessieRepository


def emit(event, **values):
    print(json.dumps({"event": event, **values}), flush=True)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


async def request(client, method, path, expected=200, **kwargs):
    response = await client.request(method, path, **kwargs)
    require(response.status_code == expected,
            f"{method} {path}: expected {expected}, received {response.status_code}")
    return response.json()


async def verify_mongo(client, account_id, completed_id, abandoned_id):
    completed = await request(client, "GET", f"/decisions/{completed_id}")
    abandoned = await request(client, "GET", f"/decisions/{abandoned_id}")
    db = get_db()
    for record, status in ((completed, "completed"), (abandoned, "abandoned")):
        require(record["account_id"] == account_id and record["outcome"] == status,
                f"Incorrect {status} decision")
        require(await db.decisions.find_one({"id": record["id"], "outcome": status}),
                f"Mongo decision missing: {status}")
        require(await db.purchase_attempts.find_one({"id": record["attempt_id"]}),
                f"Mongo attempt missing: {status}")
        require(await db.outcomes.find_one({"decision_id": record["id"], "status": status}),
                f"Mongo outcome missing: {status}")
    recent = await request(client, "GET", "/decisions/recent?limit=100")
    require({completed_id, abandoned_id} <= {row["id"] for row in recent}, "Feed missing records")
    metrics = await request(client, "GET", "/dashboard/metrics")
    require(metrics["source"] == "mongo", "Metrics did not use Mongo")
    emit("mongo_verified", completed_id=completed_id, abandoned_id=abandoned_id,
         metrics=metrics, feed=True)


async def run(args):
    gateway = NessieRepository()
    try:
        await get_db().command("ping")
        account, customer, merchant = await gateway.context_for_attempt(
            args.account_id, args.merchant_id
        )
        require(account.get("customer_id") == args.customer_id, "Account/customer mismatch")
        require(str(customer.get("_id") or customer.get("id")) == args.customer_id,
                "Customer endpoint returned a different customer")
        require(str(merchant.get("_id") or merchant.get("id")) == args.merchant_id,
                "Merchant endpoint returned a different merchant")
        require(not DecisionRepository._records, "Expected a fresh process")
        emit("preflight", mongo=True, account=True, customer=True, merchant=True)

        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://ancla-test",
                headers={"X-API-Key": settings.api_key},
            ) as client:
                ready = await request(client, "GET", "/ready")
                require(ready["ready"] and ready["database_connected"], "Backend not ready")
                if args.phase == "exercise":
                    payload = {
                        "account_id": args.account_id, "customer_id": args.customer_id,
                        "merchant_id": args.merchant_id,
                        "merchant": merchant.get("name", "Demo"), "amount": 1,
                    }
                    first = await request(client, "POST", "/purchase-attempts", json=payload)
                    require(first["context_source"] == "nessie" and first["persistence_source"] == "mongo",
                            "Decision used fallback")
                    completed_id = first["id"]
                    completed = await request(client, "POST", f"/decisions/{completed_id}/complete")
                    require(completed["outcome_source"] == "consumer_report", "Wrong outcome source")
                    require("purchase_id" not in completed, "ANCLA unexpectedly created a transaction")
                    await request(client, "POST", f"/decisions/{completed_id}/complete")
                    await request(client, "POST", f"/decisions/{completed_id}/abandon", expected=409)

                    payload["amount"] = settings.max_soft_amount
                    second = await request(client, "POST", "/purchase-attempts", json=payload)
                    require(second["decision"] == "verify", "Safety scenario must recommend verify")
                    abandoned_id = second["id"]
                    await request(client, "POST", f"/decisions/{abandoned_id}/abandon")
                    await request(client, "POST", f"/decisions/{abandoned_id}/abandon")
                    await request(client, "POST", f"/decisions/{abandoned_id}/complete", expected=409)
                    emit("exercise", completed_id=completed_id, abandoned_id=abandoned_id,
                         nessie_writes=0)
                else:
                    completed_id, abandoned_id = args.completed_id, args.abandoned_id
                await verify_mongo(client, args.account_id, completed_id, abandoned_id)
                emit("passed", phase=args.phase)
    finally:
        await close_client()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, choices=["exercise", "verify"])
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--customer-id", required=True)
    parser.add_argument("--merchant-id", required=True)
    parser.add_argument("--completed-id")
    parser.add_argument("--abandoned-id")
    args = parser.parse_args()
    if args.phase == "verify" and not (args.completed_id and args.abandoned_id):
        parser.error("verify requires --completed-id and --abandoned-id")
    try:
        asyncio.run(run(args))
    except Exception as exc:
        emit("failed", error_type=type(exc).__name__,
             check=str(exc) if isinstance(exc, AssertionError) else "Credentials suppressed")
        raise SystemExit(1) from None
