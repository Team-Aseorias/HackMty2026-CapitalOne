from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from app.schemas.evaluation import PolicyEvaluation
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.post("/run", response_model=list[PolicyEvaluation])
async def run_evaluation(seed: int = Query(default=2027, ge=2027), rows: int = Query(default=1000, ge=100, le=10000)) -> list[PolicyEvaluation]:
    return await run_in_threadpool(EvaluationService().run, rows, seed)
