from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.models.search import SearchQueryModel, SearchResponseModel
from app.services.irsa_service import (
    IRSAError,
    IRSATimeoutError,
    IRSAUpstreamError,
    search_spherex_observations,
)

router = APIRouter()

@router.get(
    "/search",
    response_model=SearchResponseModel,
    summary="Search real NASA/IRSA SPHEREx observations",
    description="Queries the official NASA/IRSA TAP service for real SPHEREx observations by celestial coordinates (RA, DEC, radius) and optional date range."
)
def search_observations(
    ra: float = Query(..., ge=0.0, le=360.0, description="Right Ascension in degrees (0..360)"),
    dec: float = Query(..., ge=-90.0, le=90.0, description="Declination in degrees (-90..90)"),
    radius_arcmin: float = Query(10.0, gt=0.0, le=120.0, description="Search radius in arcminutes (default 10)"),
    start_date: Optional[str] = Query(None, description="Optional start date ISO string (e.g. YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Optional end date ISO string (e.g. YYYY-MM-DD)")
):
    query_model = SearchQueryModel(
        ra=ra,
        dec=dec,
        radius_arcmin=radius_arcmin,
        start_date=start_date,
        end_date=end_date
    )
    
    try:
        observations = search_spherex_observations(
            ra=ra,
            dec=dec,
            radius_arcmin=radius_arcmin,
            start_date=start_date,
            end_date=end_date
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid query parameter: {e}"
        ) from e
    except IRSATimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="NASA/IRSA upstream service request timed out."
        ) from e
    except IRSAUpstreamError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"NASA/IRSA upstream service error: {e}"
        ) from e
    except IRSAError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal service error: {e}"
        ) from e

    return SearchResponseModel(
        query=query_model,
        count=len(observations),
        observations=observations
    )
