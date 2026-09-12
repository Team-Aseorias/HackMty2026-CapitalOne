from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.repositories.decision_repository import DecisionRepository
from app.repositories.nessie_repository import NessieError, NessieRepository

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("/recent")
async def recent_decisions(limit: int = 25) -> list[dict]:
    return await DecisionRepository().recent(limit=max(1, min(limit, 100)))


@router.get("/{decision_id}")
async def get_decision(decision_id: str) -> dict:
    decision = await DecisionRepository().get(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


@router.post("/{decision_id}/complete")
async def complete_decision(decision_id: str) -> dict:
    repository = DecisionRepository()
    decision = await repository.get(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    if decision.get("outcome") != "pending":
        raise HTTPException(status_code=409, detail="Decision already has an outcome")

    payload = {
        "merchant_id": decision.get("merchant_id"),
        "amount": decision["amount"],
        "purchase_date": datetime.now(timezone.utc).date().isoformat(),
        "description": f"ANCLA authorized: {decision.get('merchant', '')}",
    }
    try:
        purchase = await NessieRepository().create_purchase(decision["account_id"], payload)
        destination = "nessie"
    except NessieError as exc:
        # Local adapter preserves the causal decision log and demo semantics;
        # the response explicitly discloses that no Nessie purchase was made.
        purchase, destination = {"id": f"local-{decision_id}", "reason": str(exc)}, "local"
    updated = await repository.update(decision_id, {
        "outcome": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "purchase": purchase,
        "purchase_destination": destination,
    })
    return updated or {}


@router.post("/{decision_id}/abandon")
async def abandon_decision(decision_id: str) -> dict:
    updated = await DecisionRepository().update(decision_id, {
        "outcome": "abandoned",
        "abandoned_at": datetime.now(timezone.utc).isoformat(),
    })
    if not updated:
        raise HTTPException(status_code=404, detail="Decision not found")
    return updated
