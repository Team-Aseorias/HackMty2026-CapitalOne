from fastapi import APIRouter

from app.schemas.decision import DecisionOut
from app.schemas.purchase_attempt import PurchaseAttemptIn
from app.services.purchase_service import PurchaseService
from app.repositories.decision_repository import DecisionRepository
from app.repositories.nessie_repository import NessieError, NessieRepository

router = APIRouter(prefix="/purchase-attempts", tags=["purchase attempts"])


@router.post("", response_model=DecisionOut)
async def create_purchase_attempt(attempt: PurchaseAttemptIn) -> DecisionOut:
    repository = DecisionRepository()
    decision_history = await repository.decision_history_for_account(attempt.account_id)
    source = "nessie"
    try:
        account, history = await NessieRepository().context_for_account(attempt.account_id)
    except NessieError:
        # Nessie is simulation data, not the system of record for abandoned
        # attempts.  Keep the demo usable and label this fallback in the API.
        account, history, source = {}, await repository.history_for_account(attempt.account_id), "local"
    decision = PurchaseService().assess_with_context(
        attempt, history, account, decision_history
    )
    record = await repository.save({
        **attempt.model_dump(mode="json"),
        **decision.model_dump(),
        "features_source": source,
        "context_source": source,
        "outcome": "pending",
    })
    return decision.model_copy(update={"id": record["id"], "context_source": source})
