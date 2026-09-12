from __future__ import annotations

from datetime import datetime, timezone


class FeatureService:
    """Build decision-time features only; never include the decision/outcome."""

    def build(
        self,
        attempt: dict,
        history: list[dict],
        account: dict | None = None,
        decision_history: list[dict] | None = None,
    ) -> dict:
        now = attempt.get("occurred_at") or datetime.now(timezone.utc)
        if isinstance(now, str):
            now = datetime.fromisoformat(now.replace("Z", "+00:00"))
        amounts = [float(item.get("amount", 0)) for item in history]
        merchant = str(attempt.get("merchant", "")).lower()
        known_merchants = {str(item.get("merchant", "")).lower() for item in history}
        opened = (account or {}).get("open_date") or (account or {}).get("openDate")
        account_age_days = 365.0
        if opened:
            try:
                opened_at = datetime.fromisoformat(str(opened).replace("Z", "+00:00"))
                account_age_days = max(1.0, (now - opened_at).total_seconds() / 86_400)
            except ValueError:
                pass
        typical_amount = sum(amounts) / len(amounts) if amounts else float(attempt["amount"])
        if len(amounts) > 1:
            variance = sum((amount - typical_amount) ** 2 for amount in amounts) / len(amounts)
            amount_zscore = abs(float(attempt["amount"]) - typical_amount) / max(variance ** 0.5, 1)
        else:
            amount_zscore = 0.0
        past_decisions = decision_history or []
        verifications = [item for item in past_decisions if item.get("decision") == "verify"]
        abandons = [item for item in verifications if item.get("outcome") == "abandoned"]
        # Beta(1, 5) prior: conservative until this account has observed
        # verification outcomes, then increasingly personalized.
        abandonment_rate = (len(abandons) + 1) / (len(verifications) + 6)
        return {
            "amount": float(attempt["amount"]),
            "hour": float(now.hour),
            "weekday": float(now.weekday()),
            "merchant_novelty": 0.0 if merchant in known_merchants else 1.0,
            "recent_purchase_count": float(len(history)),
            "recent_spend": sum(amounts),
            "account_age_days": account_age_days,
            # Nessie does not expose geolocation. This is a conservative proxy
            # until the frontend provides a consented location signal.
            "distance_from_usual": abs(float(attempt["amount"]) - typical_amount) / max(typical_amount, 1) * 10,
            "average_purchase_amount": typical_amount,
            "amount_zscore": amount_zscore,
            "prior_verifications": float(len(verifications)),
            "prior_verify_abandonment_rate": abandonment_rate,
        }
