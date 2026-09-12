"""Decision queries and outcome feedback supplied by the consuming application.

ANCLA recommends allow/verify. The consumer performs any verification and
purchase; these endpoints only record its reported completion/abandonment.
"""
import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.db.mongo import is_configured
from app.repositories.decision_repository import DecisionRepository
from app.repositories.outcome_repository import insert_outcome

router = APIRouter(prefix="/decisions", tags=["decisions"])
logger = logging.getLogger(__name__)


async def _persist_outcome(decision_id: str, status: str) -> bool:
    if not is_configured():
        return False
    try:
        await insert_outcome({
            "id": str(uuid4()), "decision_id": decision_id, "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return True
    except Exception as exc:
        # Decisions is authoritative; outcomes is a reporting projection.
        logger.warning("Outcome projection failed (%s)", type(exc).__name__)
        return False


async def _decision(decision_id: str) -> dict:
    record = await DecisionRepository().get(decision_id)
    if record is None:
        raise HTTPException(404, "Decision not found")
    return record


async def _record_outcome(decision_id: str, status: str) -> dict:
    decision = await _decision(decision_id)
    if decision.get("outcome") == status:
        # Retry the projection as well if an earlier projection write failed.
        decision["outcome_projected"] = await _persist_outcome(decision_id, status)
        return decision
    if decision.get("outcome") != "pending":
        raise HTTPException(409, "Decision already has a different reported outcome")
    updated = await DecisionRepository().transition(decision_id, "pending", {
        "outcome": status,
        "completed_at" if status == "completed" else "abandoned_at":
            datetime.now(timezone.utc).isoformat(),
        "outcome_source": "consumer_report",
    })
    if updated is None:
        raise HTTPException(409, "Decision already received an outcome; reload its current state")
    updated["outcome_projected"] = await _persist_outcome(decision_id, status)
    return updated


@router.get("/recent")
async def recent_decisions(limit: int = 25) -> list[dict]:
    return await DecisionRepository().recent(limit=max(1, min(limit, 100)))


@router.get("/{decision_id}")
async def get_decision(decision_id: str) -> dict:
    return await _decision(decision_id)


@router.post("/{decision_id}/complete")
async def complete_decision(decision_id: str) -> dict:
    """Record completion reported by the consumer; never execute a purchase."""
    return await _record_outcome(decision_id, "completed")


@router.post("/{decision_id}/abandon")
async def abandon_decision(decision_id: str) -> dict:
    """Record abandonment reported by the consumer for subsequent inference."""
    return await _record_outcome(decision_id, "abandoned")
