import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

from app.db.mongo import is_configured
from app.repositories import attempt_repository
from app.repositories.decision_repository import DecisionRepository
from app.repositories.nessie_repository import NessieError, NessieRepository
from app.schemas.decision import DecisionOut
from app.schemas.purchase_attempt import PurchaseAttemptIn
from app.services.purchase_service import PurchaseService

router = APIRouter(prefix="/purchase-attempts", tags=["purchase attempts"])
logger = logging.getLogger(__name__)


@router.post("", response_model=DecisionOut)
async def create_purchase_attempt(attempt: PurchaseAttemptIn) -> DecisionOut:
    repository = DecisionRepository()
    attempt_id = str(uuid4())
    created_at = datetime.now(timezone.utc)
    decision_history = await repository.decision_history_for_account(attempt.account_id)
    history = await repository.history_for_account(attempt.account_id)
    activity = await repository.activity_for_account(attempt.account_id, created_at)
    source = "nessie"
    try:
        account, customer, merchant = await NessieRepository().context_for_attempt(
            attempt.account_id, attempt.merchant_id
        )
        customer_id = str(customer.get("_id") or customer.get("id") or "")
        if account.get("customer_id") != attempt.customer_id or customer_id != attempt.customer_id:
            raise HTTPException(403, "Account does not belong to the supplied customer")
        if attempt.merchant_id and str((merchant or {}).get("_id") or (merchant or {}).get("id")) != attempt.merchant_id:
            raise HTTPException(422, "Merchant could not be validated")
    except NessieError:
        account, source = {}, "local"
    decision = await run_in_threadpool(
        PurchaseService().assess_with_context,
        attempt, history, account, decision_history,
        context_available=bool(account or history),
        activity=activity,
    )
    if is_configured():
        attempt_document = {
            "id": attempt_id,
            **attempt.model_dump(mode="json"),
            "timestamp": (attempt.occurred_at or created_at).isoformat(),
            "created_at": created_at.isoformat(),
        }
        try:
            await attempt_repository.insert_attempt(attempt_document)
        except Exception as exc:
            logger.warning("Could not persist purchase attempt (%s)", type(exc).__name__)
            if not settings.demo_mode:
                raise HTTPException(503, "Purchase attempt storage unavailable")
    record = await repository.save({
        "attempt_id": attempt_id,
        **attempt.model_dump(mode="json"),
        **decision.model_dump(),
        "action": decision.decision,
        "features_source": source,
        "context_source": source,
        "outcome": "pending",
    })
    return decision.model_copy(update={
        "id": record["id"], "context_source": source,
        "persistence_source": record["persistence_source"],
    })
