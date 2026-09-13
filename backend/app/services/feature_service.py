from __future__ import annotations

from datetime import datetime, timezone
import math

from app.core.config import settings


def _timestamp(value) -> datetime | None:
    if not value:
        return None
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _before(row: dict, now: datetime, fields: tuple[str, ...]) -> bool:
    supplied = next((row[field] for field in fields if row.get(field)), None)
    if supplied is None:
        return False  # Unstamped historical feedback cannot prove it predates this attempt.
    stamp = _timestamp(supplied)
    return stamp is not None and stamp < now


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
        now = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
        history = [row for row in history if _before(row, now, ("completed_at", "purchase_date", "occurred_at", "timestamp", "created_at"))]
        # Ignore invalid historic amounts rather than allowing NaN or negative
        # data from an external provider to poison every derived feature.
        clean_history = []
        for row in history:
            try:
                amount = float(row.get("amount", 0))
            except (ValueError, TypeError):
                continue
            if math.isfinite(amount) and amount > 0:
                clean_history.append({**row, "amount": amount})
        history = clean_history
        amounts = [row["amount"] for row in history]
        merchant = str(attempt.get("merchant", "")).lower()
        known_merchants = {str(item.get("merchant", "")).lower() for item in history}
        known_merchant_ids = {item.get("merchant_id") for item in history if item.get("merchant_id")}
        opened = (account or {}).get("open_date") or (account or {}).get("openDate")
        account_age_days = 365.0
        if opened:
            try:
                opened_at = datetime.fromisoformat(str(opened).replace("Z", "+00:00"))
                if opened_at.tzinfo is None:
                    opened_at = opened_at.replace(tzinfo=timezone.utc)
                account_age_days = max(1.0, (now - opened_at).total_seconds() / 86_400)
            except ValueError:
                pass
        typical_amount = sum(amounts) / len(amounts) if amounts else float(attempt["amount"])
        amount_zscore = abs(math.log(float(attempt["amount"]) / max(typical_amount, 1))) / 0.75
        past_decisions = [row for row in (decision_history or [])
                          if row.get("outcome") in {"completed", "abandoned"}
                          and _before(row, now, ("completed_at", "abandoned_at"))]
        verifications = [item for item in past_decisions if item.get("action", item.get("decision")) == "verify"]
        abandons = [item for item in verifications if item.get("outcome") == "abandoned"]
        # Beta(1, 5) prior: conservative until this account has observed
        # verification outcomes, then increasingly personalized.
        abandonment_rate = (
            (len(abandons) + 1) / (len(verifications) + 6)
            if len(verifications) >= settings.min_personalization_history else 1 / 6
        )
        return {
            "amount": float(attempt["amount"]),
            "hour": float(now.hour),
            "weekday": float(now.weekday()),
            "merchant_novelty": 0.0 if merchant in known_merchants or attempt.get("merchant_id") in known_merchant_ids else 1.0,
            "recent_purchase_count": float(len(history)),
            "recent_spend": sum(amounts),
            "account_age_days": account_age_days,
            # Nessie does not expose geolocation. This is a conservative proxy
            # until the frontend provides a consented location signal.
            "distance_from_usual": abs(float(attempt["amount"]) - typical_amount) / max(typical_amount, 1) * 10,
            "average_purchase_amount": typical_amount,
            "amount_zscore": amount_zscore,
            "prior_verifications": float(len(verifications)),
            "prior_verify_abandons": float(len(abandons)),
            "prior_verify_abandonment_rate": abandonment_rate,
        }
