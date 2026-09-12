from fastapi import APIRouter

from app.schemas.evaluation import PolicyEvaluation
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.post("/run", response_model=list[PolicyEvaluation])
async def run_evaluation() -> list[PolicyEvaluation]:
    return EvaluationService().run()
