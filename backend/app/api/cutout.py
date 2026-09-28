import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.config import settings
from app.models.cutout import CutoutRequestModel, CutoutResponseModel
from app.models.search import SPHERExObservationModel
from app.services.cutout_service import (
    CutoutDownloadError,
    CutoutError,
    DatalinkResolutionError,
    fetch_spherex_cutout,
    sanitize_identifier,
)
from app.services.fits_service import (
    FITSError,
    FITSStructureError,
    generate_preview,
    inspect_fits_cutout,
)
from app.services.irsa_service import (
    IRSATimeoutError,
    IRSAUpstreamError,
    search_spherex_observations,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/cutout",
    response_model=CutoutResponseModel,
    summary="Retrieve and inspect a real SPHEREx FITS cutout",
    description="Resolves observation Datalink to an on-premises FITS image, downloads a small spatial cutout via the IRSA Cutout Service, inspects HDU WCS, and creates a preview PNG."
)
def create_cutout(request: CutoutRequestModel):
    # Validate request
    if request.cutout_size_deg <= 0.0 or request.cutout_size_deg > 1.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"cutout_size_deg must be between 0.001 and 1.0 degrees, got {request.cutout_size_deg}"
        )

    datalink_url = request.datalink_url
    obs_time_utc = request.observation_time_utc
    bandpass = request.bandpass

    # If Datalink URL not provided, search for observation by ID in IRSA archive
    if not datalink_url:
        try:
            candidates = search_spherex_observations(
                ra=request.ra,
                dec=request.dec,
                radius_arcmin=30.0,
                max_records=500
            )
            matching = [o for o in candidates if o.observation_id == request.observation_id]
            if not matching:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Observation '{request.observation_id}' not found covering RA={request.ra}, DEC={request.dec}."
                )
            chosen = matching[0]
            datalink_url = chosen.data_access_url
            obs_time_utc = chosen.observation_time_utc or obs_time_utc
            bandpass = chosen.bandpass or bandpass
        except IRSATimeoutError as e:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="NASA/IRSA service timed out during observation lookup."
            ) from e
        except IRSAUpstreamError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"NASA/IRSA search error: {e}"
            ) from e

    obs_model = SPHERExObservationModel(
        observation_id=request.observation_id,
        ra=request.ra,
        dec=request.dec,
        bandpass=bandpass,
        data_access_url=datalink_url,
        observation_time_utc=obs_time_utc
    )

    cache_dir = Path(settings.CACHE_DIR)
    previews_dir = cache_dir / "previews"

    # Fetch cutout
    try:
        fits_path, cached = fetch_spherex_cutout(
            observation=obs_model,
            ra=request.ra,
            dec=request.dec,
            size_deg=request.cutout_size_deg,
            cache_dir=cache_dir
        )
    except DatalinkResolutionError as e:
        logger.error("Datalink resolution failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Datalink resolution error: {e}"
        ) from e
    except CutoutDownloadError as e:
        logger.error("Cutout download failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cutout service download error: {e}"
        ) from e
    except CutoutError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cutout retrieval error: {e}"
        ) from e

    # Inspect FITS and WCS
    try:
        fits_info = inspect_fits_cutout(fits_path, center_ra=request.ra, center_dec=request.dec)
    except FITSStructureError as e:
        logger.error("FITS structure error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"FITS structure error in downloaded file: {e}"
        ) from e
    except FITSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"FITS inspection error: {e}"
        ) from e

    # Generate preview
    preview_filename = f"{fits_path.stem}_preview.png"
    preview_path = previews_dir / preview_filename
    try:
        title = f"SPHEREx {request.observation_id} ({bandpass or 'Image'})"
        generate_preview(
            fits_path=fits_path,
            output_png_path=preview_path,
            center_ra=request.ra,
            center_dec=request.dec,
            title=title
        )
    except Exception as e:
        logger.warning("Preview generation warning: %s", e)

    return CutoutResponseModel(
        status="success",
        observation_id=request.observation_id,
        observation_time_utc=obs_time_utc,
        bandpass=bandpass,
        fits_filename=fits_path.name,
        fits_relative_path=f"cache/{fits_path.name}",
        preview_filename=preview_path.name,
        preview_relative_path=f"cache/previews/{preview_path.name}",
        image_hdu_index=fits_info["science_index"],
        image_hdu_name=fits_info["science_name"],
        image_shape=fits_info["image_shape"],
        wcs_available=fits_info["wcs_available"],
        wcs_summary=fits_info["wcs_summary"],
        target_pixel_coords=fits_info["target_pixel_coords"],
        center_ra=request.ra,
        center_dec=request.dec,
        cutout_size_deg=request.cutout_size_deg,
        cached=cached
    )


@router.get(
    "/preview/{filename}",
    summary="Serve generated FITS preview or visualization image",
    description="Returns generated preview PNGs or motion plots safely."
)
def get_preview_image(filename: str):
    cache_dir = Path(settings.CACHE_DIR)
    # Check in previews/ and motion/ subdirectories, or cache_dir directly
    candidates = [
        cache_dir / "previews" / filename,
        cache_dir / "motion" / filename,
        cache_dir / filename,
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            return FileResponse(p, media_type="image/png")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Preview image '{filename}' not found.")
