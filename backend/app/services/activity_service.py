"""Account-level velocity controls. These rules never manufacture fraud labels."""
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.schemas.decision import ActivityEvidence, SafetyCheck
from app.services.feature_service import _timestamp


def activity_from_records(records: list[dict], now: datetime) -> ActivityEvidence:
    now = now.astimezone(timezone.utc)
    start = now - timedelta(seconds=settings.activity_window_seconds)
    seen = set()
    attempts = abandons = 0
    for record in records:
        identifier = record.get("id")
        if identifier and identifier in seen:
            continue
        if identifier:
            seen.add(identifier)
        # Use server receipt time, never a caller-controlled purchase timestamp.
        created = _timestamp(record.get("created_at"))
        if created is not None and start <= created <= now:
            attempts += 1
        # Count recent abandonment events even if their attempt started earlier.
        abandoned = _timestamp(record.get("abandoned_at"))
        if (record.get("action", record.get("decision")) == "verify"
                and record.get("outcome") == "abandoned"
                and created is not None and created <= now
                and abandoned is not None and created <= abandoned
                and start <= abandoned <= now):
            abandons += 1
    return ActivityEvidence(window_seconds=settings.activity_window_seconds,
                            prior_attempts=attempts, prior_verify_abandons=abandons)


def activity_checks(activity: ActivityEvidence) -> list[SafetyCheck]:
    return [
        SafetyCheck(code=code, observed=value, threshold=threshold, triggered=value >= threshold)
        for code, value, threshold in (
            ("attempt_velocity", activity.prior_attempts + 1, settings.max_window_attempts),
            ("verify_abandon_velocity", activity.prior_verify_abandons, settings.max_window_verify_abandons),
        )
    ]
