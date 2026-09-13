"""Controlled, anonymous histories used to demonstrate personalization.

These profiles are fixtures, not Capital One customers or fraud labels. Live
outcomes reported through the demo are appended by the decision repository.
"""
from datetime import datetime, timedelta, timezone


PROFILES = {
    "estable": {
        "label": "Cliente estable",
        "description": "Historial inicial: ocho verificaciones resueltas y ningún abandono reportado.",
        "abandons": 0,
    },
    "mixto": {
        "label": "Cliente mixto",
        "description": "Historial inicial: ocho verificaciones resueltas y tres abandonos reportados.",
        "abandons": 3,
    },
    "friccion": {
        "label": "Cliente con fricción",
        "description": "Historial inicial: ocho verificaciones resueltas y seis abandonos reportados.",
        "abandons": 6,
    },
}


def get_profile(key: str) -> dict | None:
    profile = PROFILES.get(key)
    if profile is None:
        return None
    return {
        "key": key,
        "customer_id": f"demo-customer-{key}",
        "account_id": f"demo-account-{key}",
        **profile,
    }


def profile_context(profile: dict) -> dict:
    # All profiles intentionally share the same non-friction context so the
    # comparison isolates verification history.
    return {
        "customer_id": profile["customer_id"],
        "open_date": "2022-01-15T00:00:00+00:00",
    }


def controlled_purchase_history(now: datetime) -> list[dict]:
    now = now.astimezone(timezone.utc)
    amounts = (280, 305, 295, 310, 300, 290)
    return [
        {
            "amount": amount,
            "merchant": "Farmacias Demo",
            "completed_at": (now - timedelta(days=45 - index * 5)).isoformat(),
        }
        for index, amount in enumerate(amounts)
    ]


def controlled_decision_history(profile: dict, now: datetime) -> list[dict]:
    now = now.astimezone(timezone.utc)
    abandons = int(profile["abandons"])
    rows = []
    for index in range(8):
        abandoned = index < abandons
        resolved_at = now - timedelta(days=20 - index)
        rows.append({
            "id": f"fixture-{profile['key']}-{index}",
            "account_id": profile["account_id"],
            "action": "verify",
            "outcome": "abandoned" if abandoned else "completed",
            "abandoned_at" if abandoned else "completed_at": resolved_at.isoformat(),
            "created_at": (resolved_at - timedelta(minutes=2)).isoformat(),
        })
    return rows
