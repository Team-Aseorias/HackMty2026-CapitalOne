"""Anonymous demo profiles with controlled verification histories."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.repositories.decision_repository import DecisionRepository
from app.schemas.decision import DecisionOut
from app.schemas.demo_profile import DemoProfileOut, DemoPurchaseAttemptIn
from app.schemas.purchase_attempt import PurchaseAttemptIn
from app.services.demo_profile_service import (
    PROFILES,
    controlled_decision_history,
    controlled_purchase_history,
    get_profile,
    profile_context,
)
from app.services.purchase_service import PurchaseService


router = APIRouter(prefix="/demo-profiles", tags=["demo profiles"])


def _require_enabled() -> None:
    if not settings.enable_demo_profiles:
        raise HTTPException(404, "Demo profiles are disabled")


@router.get("", response_model=list[DemoProfileOut])
async def list_demo_profiles() -> list[DemoProfileOut]:
    _require_enabled()
    repository = DecisionRepository()
    profiles = []
    for key in PROFILES:
        profile = get_profile(key)
        assert profile is not None
        live = await repository.decision_history_for_account(profile["account_id"])
        live_verify = [
            row for row in live
            if row.get("action", row.get("decision")) == "verify"
        ]
        profiles.append(DemoProfileOut(
            key=key,
            label=profile["label"],
            description=profile["description"],
            resolved_verifications=8 + len(live_verify),
            reported_abandons=int(profile["abandons"]) + sum(
                row.get("outcome") == "abandoned" for row in live_verify
            ),
        ))
    return profiles


@router.post("/{profile_key}/purchase-attempts", response_model=DecisionOut)
async def create_demo_profile_attempt(
    profile_key: str, payload: DemoPurchaseAttemptIn,
) -> DecisionOut:
    _require_enabled()
    profile = get_profile(profile_key)
    if profile is None:
        raise HTTPException(404, "Demo profile not found")

    repository = DecisionRepository()
    created_at = datetime.now(timezone.utc)
    live_decisions = await repository.decision_history_for_account(profile["account_id"])
    live_purchases = await repository.history_for_account(profile["account_id"])
    activity = await repository.activity_for_account(profile["account_id"], created_at)
    decision_history = [
        *controlled_decision_history(profile, created_at),
        *live_decisions,
    ]
    purchase_history = [*controlled_purchase_history(created_at), *live_purchases]
    attempt = PurchaseAttemptIn(
        customer_id=profile["customer_id"],
        account_id=profile["account_id"],
        merchant=payload.merchant,
        amount=payload.amount,
        occurred_at=created_at,
    )
    decision = await run_in_threadpool(
        PurchaseService().assess_with_context,
        attempt,
        purchase_history,
        profile_context(profile),
        decision_history,
        context_available=True,
        activity=activity,
    )
    record = await repository.save({
        **attempt.model_dump(mode="json"),
        **decision.model_dump(),
        "action": decision.decision,
        "demo_profile_key": profile_key,
        "features_source": "controlled_demo",
        "context_source": "local",
        "outcome": "pending",
    })
    return decision.model_copy(update={
        "id": record["id"],
        "context_source": "local",
        "persistence_source": record["persistence_source"],
        "demo_profile_key": profile_key,
    })
