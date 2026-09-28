"""
FastAPI router for Known Moving Object validation (3I/ATLAS).

GET /api/known-object/3i-atlas

Validates the SPHEREx moving-object pipeline against the official NASA/IPAC IRSA
observation table of confirmed interstellar comet 3I/ATLAS.
Distinguishes external ephemeris predictions from independent image measurements.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings
from app.services.known_objects import (
    KnownObjectError,
    KnownObjectObservation,
    TargetAssociationResult,
    associate_target_source,
    get_known_object_pair,
    generate_known_object_visualization,
    to_spherex_observation,
)
from app.services.cutout_service import fetch_spherex_cutout
from app.services.fits_service import inspect_fits_cutout, generate_preview
from app.services.source_detection import load_science_image, detect_sources

logger = logging.getLogger(__name__)
router = APIRouter()


class KnownObjectValidationResponse(BaseModel):
    """Structured response for 3I/ATLAS known-object validation."""
    target_name: str = Field("3I/ATLAS", description="Name of the confirmed object")
    object_description: str = Field(
        "Interstellar comet 3I/ATLAS validated using official NASA/IPAC IRSA SPHEREx observation table",
        description="Scientific description of object"
    )
    status: str = Field("success", description="Execution status")
    epoch_1: TargetAssociationResult = Field(..., description="Target association result for Epoch 1")
    epoch_2: TargetAssociationResult = Field(..., description="Target association result for Epoch 2")
    observation_1: KnownObjectObservation = Field(..., description="Metadata for Epoch 1 observation")
    observation_2: KnownObjectObservation = Field(..., description="Metadata for Epoch 2 observation")
    two_epoch_motion_measurable: bool = Field(
        False,
        description="Whether two-epoch motion could be independently measured"
    )
    motion_decision: str = Field(
        ...,
        description="Explicit scientific statement on two-epoch motion measurement"
    )
    preview_url_1: Optional[str] = Field(None, description="URL for Epoch 1 preview PNG")
    preview_url_2: Optional[str] = Field(None, description="URL for Epoch 2 preview PNG")
    validation_plot_url: Optional[str] = Field(None, description="URL for side-by-side comparison plot PNG")
    sources_detected_epoch_1: int = Field(0, description="Total sources detected in Epoch 1")
    sources_detected_epoch_2: int = Field(0, description="Total sources detected in Epoch 2")
    warnings: List[str] = Field(default_factory=list, description="Scientific warnings and notices")
    scientific_disclaimer: str = Field(
        (
            "SCIENTIFIC DISCLAIMER: Known-object validation mode compares detected image sources "
            "with official NASA/IPAC IRSA ephemeris positions. Motion between epochs is only computed "
            "when the target is independently and reliably detected in both epochs."
        ),
        description="Mandatory scientific disclaimer"
    )


@router.get(
    "/known-object/3i-atlas",
    response_model=KnownObjectValidationResponse,
    summary="Validate pipeline with confirmed interstellar comet 3I/ATLAS",
    description=(
        "Retrieves the validation pair from the official NASA/IPAC IRSA SPHEREx 3I/ATLAS observation table, "
        "inspects FITS cutouts, runs source detection, associates target centroids with predicted coordinates, "
        "and evaluates two-epoch motion measurability."
    )
)
def validate_3i_atlas() -> KnownObjectValidationResponse:
    cache_dir = Path(settings.CACHE_DIR)
    previews_dir = cache_dir / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)

    try:
        obs1, obs2 = get_known_object_pair(cache_dir=cache_dir)
    except KnownObjectError as e:
        logger.error("Failed to load 3I/ATLAS observation table: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to load official 3I/ATLAS observation table: {e}"
        ) from e

    # Retrieve / load cutouts for both epochs
    cutouts = []
    for obs in (obs1, obs2):
        sph_obs = to_spherex_observation(obs)
        try:
            fits_path, _ = fetch_spherex_cutout(
                observation=sph_obs,
                ra=obs.comet_ra,
                dec=obs.comet_dec,
                size_deg=0.05,
                cache_dir=cache_dir,
            )
            # Ensure preview PNG exists
            preview_path = previews_dir / f"{fits_path.stem}_preview.png"
            if not preview_path.exists():
                generate_preview(
                    fits_path=fits_path,
                    output_png_path=preview_path,
                    center_ra=obs.comet_ra,
                    center_dec=obs.comet_dec,
                    title=f"3I/ATLAS {obs.obs_id} ({obs.bandpass})"
                )
            cutouts.append((obs, fits_path, preview_path))
        except Exception as e:
            logger.error("Failed to fetch cutout for %s: %s", obs.obs_id, e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to retrieve SPHEREx image for {obs.obs_id}: {e}"
            ) from e

    (_, p1, prev1), (_, p2, prev2) = cutouts

    # Run source detection and target association
    try:
        d1, w1, m1 = load_science_image(p1, obs1.comet_ra, obs1.comet_dec)
        sources_1 = detect_sources(d1, w1, detection_sigma=3.0, variance=m1.get("variance"))
        target_res_1 = associate_target_source(
            detected_sources=sources_1,
            predicted_ra=obs1.comet_ra,
            predicted_dec=obs1.comet_dec,
            max_separation_arcsec=15.0,
            target_name="3I/ATLAS",
            wcs=w1,
        )
    except Exception as e:
        logger.warning("Error evaluating Epoch 1: %s", e)
        target_res_1 = TargetAssociationResult(
            target_name="3I/ATLAS",
            predicted_ra=obs1.comet_ra,
            predicted_dec=obs1.comet_dec,
            status="NOT_DETECTED",
            evaluation_note=f"Detection error: {e}",
        )
        sources_1 = []

    try:
        d2, w2, m2 = load_science_image(p2, obs2.comet_ra, obs2.comet_dec)
        sources_2 = detect_sources(d2, w2, detection_sigma=3.0, variance=m2.get("variance"))
        target_res_2 = associate_target_source(
            detected_sources=sources_2,
            predicted_ra=obs2.comet_ra,
            predicted_dec=obs2.comet_dec,
            max_separation_arcsec=15.0,
            target_name="3I/ATLAS",
            wcs=w2,
        )
    except Exception as e:
        logger.warning("Error evaluating Epoch 2: %s", e)
        target_res_2 = TargetAssociationResult(
            target_name="3I/ATLAS",
            predicted_ra=obs2.comet_ra,
            predicted_dec=obs2.comet_dec,
            status="NOT_DETECTED",
            evaluation_note=f"Detection error: {e}",
        )
        sources_2 = []

    # Generate validation comparison plot
    val_plot_path = previews_dir / "3I_ATLAS_validation.png"
    try:
        generate_known_object_visualization(
            fits_path_1=p1,
            fits_path_2=p2,
            pred_ra_1=obs1.comet_ra,
            pred_dec_1=obs1.comet_dec,
            pred_ra_2=obs2.comet_ra,
            pred_dec_2=obs2.comet_dec,
            detected_1=target_res_1.matched_source,
            detected_2=target_res_2.matched_source,
            output_png_path=val_plot_path,
            title="3I/ATLAS SPHEREx Validation (2025-08-07)"
        )
    except Exception as e:
        logger.warning("Validation visualization warning: %s", e)

    both_detected = (
        target_res_1.status.value == "DETECTED"
        and target_res_2.status.value == "DETECTED"
    )
    one_detected_one_not = (
        (target_res_1.status.value == "DETECTED" and target_res_2.status.value != "DETECTED")
        or (target_res_1.status.value != "DETECTED" and target_res_2.status.value == "DETECTED")
    )

    warnings = []
    if one_detected_one_not:
        motion_decision = "Two-epoch motion not measurable because the target was not reliably detected in both epochs."
        warnings.append(motion_decision)
    elif both_detected:
        motion_decision = "Target reliably detected in both epochs. Two-epoch motion measurable."
    else:
        motion_decision = "Target was not reliably detected in either epoch. Two-epoch motion not measurable."
        warnings.append(motion_decision)

    return KnownObjectValidationResponse(
        target_name="3I/ATLAS",
        object_description="Interstellar comet 3I/ATLAS validated using official NASA/IPAC IRSA SPHEREx observation table",
        status="success",
        epoch_1=target_res_1,
        epoch_2=target_res_2,
        observation_1=obs1,
        observation_2=obs2,
        two_epoch_motion_measurable=both_detected,
        motion_decision=motion_decision,
        preview_url_1=f"/api/preview/{prev1.name}",
        preview_url_2=f"/api/preview/{prev2.name}",
        validation_plot_url=f"/api/preview/{val_plot_path.name}" if val_plot_path.exists() else None,
        sources_detected_epoch_1=len(sources_1),
        sources_detected_epoch_2=len(sources_2),
        warnings=warnings,
    )
