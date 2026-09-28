"""
FastAPI endpoint for the two-epoch motion analysis pipeline.

POST /api/analyze-motion

Accepts two FITS file references (from Step 2 cutouts) and runs the
complete source detection → cross-matching → motion analysis pipeline.
Returns structured JSON with candidates, statistics, and visualization paths.
"""
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.models.motion import MotionAnalysisRequest, MotionAnalysisResult
from app.services.motion_analysis import MotionAnalysisError, run_motion_analysis

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/analyze-motion",
    response_model=MotionAnalysisResult,
    summary="Run two-epoch motion analysis on cached SPHEREx FITS cutouts",
    description=(
        "Analyzes two real SPHEREx FITS cutouts from different observation epochs "
        "to detect, cross-match, and classify moving-object candidates. "
        "Uses DAOStarFinder for source detection, Astropy SkyCoord for sky-coordinate "
        "cross-matching, and generates motion trail visualizations. "
        "Results are structured as moving-object candidates requiring further investigation. "
        "This endpoint does NOT claim to detect Planet X or any specific object."
    ),
)
def analyze_motion(request: MotionAnalysisRequest) -> MotionAnalysisResult:
    """
    Execute the full two-epoch motion analysis pipeline.

    Expects cached FITS cutout paths from Step 2's /api/cutout endpoint.
    """
    def _resolve_fits(p_str: str) -> Path:
        p = Path(p_str)
        if p.exists() and p.is_file():
            return p
        cache_dir = Path(settings.CACHE_DIR)
        cand1 = cache_dir / p_str
        if cand1.exists() and cand1.is_file():
            return cand1
        cand2 = cache_dir / p.name
        if cand2.exists() and cand2.is_file():
            return cand2
        return p

    fits_1 = _resolve_fits(request.fits_path_1)
    fits_2 = _resolve_fits(request.fits_path_2)

    if not fits_1.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FITS file for epoch 1 not found: {request.fits_path_1}"
        )

    if not fits_2.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FITS file for epoch 2 not found: {request.fits_path_2}"
        )

    request.fits_path_1 = str(fits_1.resolve())
    request.fits_path_2 = str(fits_2.resolve())

    # Validate at least one form of timestamp
    has_time_1 = request.timestamp_utc_1 or request.timestamp_mjd_1 is not None
    has_time_2 = request.timestamp_utc_2 or request.timestamp_mjd_2 is not None

    if not has_time_1 or not has_time_2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Both epochs require at least one timestamp "
                "(timestamp_utc or timestamp_mjd) to compute time differences."
            )
        )

    try:
        result = run_motion_analysis(request)
    except MotionAnalysisError as e:
        logger.error("Motion analysis failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Motion analysis error: {e}"
        ) from e
    except Exception as e:
        logger.error("Unexpected error during motion analysis: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error during motion analysis: {e}"
        ) from e

    return result
