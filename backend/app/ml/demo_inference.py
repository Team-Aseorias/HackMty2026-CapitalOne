"""Offline pitch examples: paired profiles and a safety-limit counterexample."""
import json

from app.schemas.purchase_attempt import PurchaseAttemptIn
from app.services.purchase_service import PurchaseService


def examples():
    service = PurchaseService()
    history = [{"merchant": "shop", "amount": 120, "purchase_date": "2026-09-01"} for _ in range(5)]
    results = []
    for name, abandoned, amount in (
        ("Same transaction: no prior abandonment", False, 150),
        ("Same transaction: frequent prior abandonment", True, 150),
        ("Frequent abandonment: amount exceeds safety limit", True, 1000),
    ):
        feedback = [{
            "action": "verify", "outcome": "abandoned" if abandoned else "completed",
            "abandoned_at" if abandoned else "completed_at": "2026-09-10T12:00:00Z",
        } for _ in range(12)]
        decision = service.assess_with_context(
            PurchaseAttemptIn(customer_id="demo", account_id="demo", merchant="shop", amount=amount,
                              occurred_at="2026-09-12T12:00:00Z"),
            history, {"open_date": "2025-01-01"}, feedback,
        )
        results.append({"scenario": name, "amount": amount, **decision.model_dump()})
    return {"source": "synthetic illustrative profiles; no external accounts accessed", "examples": results}


if __name__ == "__main__":
    print(json.dumps(examples(), indent=2, allow_nan=False))
