import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.db.mongo import is_configured
from app.repositories.decision_repository import DecisionRepository
from app.repositories.nessie_repository import NessieError, NessieRepository
from app.repositories.outcome_repository import insert_outcome

router = APIRouter(prefix="/decisions", tags=["decisions"])
logger = logging.getLogger(__name__)


async def _persist_outcome(
    decision_id: str, status: str, nessie_purchase_id: str | None = None
) -> None:
    if not is_configured():
        return
    try:
        await insert_outcome({
            "id": str(uuid4()),
            "decision_id": decision_id,
            "status": status,
            "nessie_purchase_id": nessie_purchase_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        logger.warning("Could not persist decision outcome: %s", exc)


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
    await _persist_outcome(decision_id, "completed", purchase.get("id"))
    return updated or {}


@router.post("/{decision_id}/abandon")
async def abandon_decision(decision_id: str) -> dict:
    updated = await DecisionRepository().update(decision_id, {
        "outcome": "abandoned",
        "abandoned_at": datetime.now(timezone.utc).isoformat(),
    })
    if not updated:
        raise HTTPException(status_code=404, detail="Decision not found")
    await _persist_outcome(decision_id, "abandoned")
    return updated
