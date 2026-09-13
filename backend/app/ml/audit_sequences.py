"""Controlled longitudinal sensitivity checks; no external data or writes."""
import json
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.services.causal_service import CausalService
from app.services.feature_service import FeatureService
from app.services.risk_service import RiskService
from app.services.activity_service import activity_from_records
from app.services.purchase_service import PurchaseService
from app.schemas.purchase_attempt import PurchaseAttemptIn


NOW = datetime(2026, 9, 12, 12, tzinfo=timezone.utc)


def sequence(amount=600, gap_minutes=1, maximum=50):
    history = [
        {"amount": amount, "merchant": "shop", "completed_at": "2026-09-01T12:00:00+00:00"}
        for _ in range(5)
    ]
    account = {"open_date": "2025-01-01"}
    attempt = {"amount": amount, "merchant": "shop", "occurred_at": NOW}
    rows = []
    for n in range(maximum + 1):
        feedback = [
            {"id": f"d{i}", "account_id": "demo", "action": "verify", "outcome": "abandoned",
             "created_at": (NOW - timedelta(minutes=(i + 1) * gap_minutes, seconds=10)).isoformat(),
             "abandoned_at": (NOW - timedelta(minutes=(i + 1) * gap_minutes)).isoformat()}
            for i in range(n)
        ]
        features = FeatureService().build(attempt, history, account, feedback)
        allow, verify, ca, cv = CausalService().predict(features)
        activity = activity_from_records(feedback, NOW)
        decision = PurchaseService().assess_with_context(
            PurchaseAttemptIn(customer_id="demo", account_id="demo", **attempt),
            history, account, feedback, activity=activity,
        )
        rows.append({
            "prior_resolved_verifications": n,
            "smoothed_history_rate": features["prior_verify_abandonment_rate"],
            "risk_score": RiskService().score(features),
            "estimated_cost_allow": allow, "estimated_cost_verify": verify,
            "legitimate_abandonment_allow": 1 - ca,
            "legitimate_abandonment_verify": 1 - cv,
            "delta_verify_cost": verify - rows[-1]["estimated_cost_verify"] if rows else 0,
            "recent_prior_attempts": activity.prior_attempts,
            "recent_prior_verify_abandons": activity.prior_verify_abandons,
            "decision": decision.decision,
            "triggered_rules": [check.code for check in decision.safety_checks if check.triggered],
            "model_warnings": decision.model_warnings,
        })
    return rows


def audit():
    rapid = sequence()
    spaced = sequence(gap_minutes=1440)
    return {
        "scope": "Controlled synthetic sensitivity, fixed account/merchant/amount/hour; not calibration against real users",
        "amount": 600,
        "thresholds": {
            "risk": settings.max_soft_risk, "loss": settings.max_soft_expected_loss,
            "amount": settings.max_soft_amount,
            "verification_cost": settings.verify_cost,
            "abandonment_cost_rate": settings.abandonment_cost_rate,
        },
        "sequence": rapid,
        "rapid_and_spaced_model_predictions_identical": all(
            a[key] == b[key] for a, b in zip(rapid, spaced)
            for key in ("risk_score", "estimated_cost_verify", "legitimate_abandonment_verify")
        ),
        "spaced_sequence": spaced,
        "cost_decreases_at": [r["prior_resolved_verifications"] for r in rapid if r["delta_verify_cost"] < -1e-9],
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, allow_nan=False))
