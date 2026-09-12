# backend/scripts/test_repositories.py
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.db.mongo import get_db, close_client, PURCHASE_ATTEMPTS, DECISIONS, OUTCOMES
from app.repositories import attempt_repository, decision_repository, outcome_repository


async def main():
    db = get_db()
    suffix = uuid4().hex[:8]

    # ---------- attempt_repository ----------
    print("== attempt_repository ==")
    attempt = {
        "id": f"att_{suffix}",
        "account_id": f"acc_{suffix}",
        "customer_id": f"cus_{suffix}",
        "merchant_id": f"mer_{suffix}",
        "amount": 450.0,
        "currency": "MXN",
        "category": "pharmacy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await attempt_repository.insert_attempt(attempt)
    print("  insert ok")

    got = await attempt_repository.get_attempt_by_id(attempt["id"])
    assert got and got["id"] == attempt["id"], "get_attempt_by_id falló"
    print("  get by id ok")

    listed = await attempt_repository.list_recent_attempts(attempt["account_id"])
    assert any(a["id"] == attempt["id"] for a in listed), "list_recent_attempts falló"
    print(f"  list recent ok ({len(listed)} docs)")

    # ---------- decision_repository ----------
    print("== decision_repository ==")
    decision = {
        "id": f"dec_{suffix}",
        "attempt_id": attempt["id"],
        "action": "verify",
        "policy": "causal",
        "risk_prob": 0.82,
        "expected_cost_allow": 120.0,
        "expected_cost_verify": 40.0,
        "effect_verify": 80.0,
        "explanation": "smoke test",
        "context_snapshot": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await decision_repository.insert_decision(decision)
    print("  insert ok")

    got = await decision_repository.get_decision_by_id(decision["id"])
    assert got and got["id"] == decision["id"], "get_decision_by_id falló"
    print("  get by id ok")

    got = await decision_repository.get_decision_by_attempt_id(attempt["id"])
    assert got and got["attempt_id"] == attempt["id"], "get_decision_by_attempt_id falló"
    print("  get by attempt id ok")

    listed = await decision_repository.list_recent_decisions(limit=10)
    assert any(d["id"] == decision["id"] for d in listed), "list_recent_decisions falló"
    print(f"  list recent ok ({len(listed)} docs)")

    listed = await decision_repository.list_decisions_by_action("verify", limit=10)
    assert any(d["id"] == decision["id"] for d in listed), "list_decisions_by_action falló"
    print(f"  list by action ok ({len(listed)} docs)")

    # ---------- outcome_repository ----------
    print("== outcome_repository ==")
    outcome = {
        "id": f"out_{suffix}",
        "decision_id": decision["id"],
        "status": "completed",
        "nessie_purchase_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await outcome_repository.insert_outcome(outcome)
    print("  insert ok")

    got = await outcome_repository.get_outcome_by_decision_id(decision["id"])
    assert got and got["decision_id"] == decision["id"], "get_outcome_by_decision_id falló"
    print("  get by decision id ok")

    listed = await outcome_repository.list_recent_outcomes(limit=10)
    assert any(o["id"] == outcome["id"] for o in listed), "list_recent_outcomes falló"
    print(f"  list recent ok ({len(listed)} docs)")

    n = await outcome_repository.count_by_status("completed")
    print(f"  count completed = {n}")

    # ---------- cleanup ----------
    print("== cleanup ==")
    await db[PURCHASE_ATTEMPTS].delete_one({"id": attempt["id"]})
    await db[DECISIONS].delete_one({"id": decision["id"]})
    await db[OUTCOMES].delete_one({"id": outcome["id"]})
    print("  docs de prueba eliminados")

    await close_client()
    print("\nRepositorios OK")


if __name__ == "__main__":
    asyncio.run(main())