"""
FastAPI router for the Hypothesis Update & New Observation analysis pipeline.

Endpoints:
- POST /api/hypothesis/update: Evaluate a new observation against working hypothesis
- GET  /api/hypothesis/scenarios: Retrieve the 4 controlled challenge scenarios
"""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, status

from app.models.hypothesis import (
    ChallengeScenarioInfo,
    HypothesisUpdateRequest,
    HypothesisUpdateResult,
)
from app.services.hypothesis_analysis import (
    evaluate_hypothesis_update,
    get_challenge_scenarios,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/hypothesis/update",
    response_model=HypothesisUpdateResult,
    summary="Evaluate new observation against candidate hypothesis",
    description=(
        "Incorporate a new observation (Epoch 3) into an existing candidate hypothesis. "
        "Calculates trajectory extrapolation, astrometric residuals, and applies explicit deterministic rules "
        "to classify the updated hypothesis as STRENGTHENED, WEAKENED, CHANGED, or INCONCLUSIVE."
    ),
)
def update_hypothesis(request: HypothesisUpdateRequest) -> HypothesisUpdateResult:
    try:
        result = evaluate_hypothesis_update(request)
        return result
    except Exception as e:
        logger.error("Error evaluating hypothesis update: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hypothesis evaluation failed: {e}",
        ) from e


@router.get(
    "/hypothesis/scenarios",
    response_model=List[ChallengeScenarioInfo],
    summary="Get controlled demonstration challenge scenarios",
    description=(
        "Returns pre-configured demonstration challenge scenarios illustrating "
        "STRENGTHENED, WEAKENED, CHANGED, and INCONCLUSIVE hypothesis updates."
    ),
)
def list_challenge_scenarios() -> List[ChallengeScenarioInfo]:
    return get_challenge_scenarios()
