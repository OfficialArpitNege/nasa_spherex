#!/usr/bin/env python3
"""
Interactive CLI for SPHEREx Moving Object Explorer.
Queries real NASA/IRSA observations, groups them by UTC date,
and allows multi-epoch selection for temporal comparison.
"""

import logging
from pathlib import Path
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

from app.cli_helpers import (
    group_observations_by_date,
    parse_date_indices,
    select_representative_observation,
    validate_dec,
    validate_ra,
    validate_radius,
)
from app.models.search import SPHERExObservationModel
from app.services.irsa_service import IRSAError, search_spherex_observations

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def prompt_coordinates(
    input_func: Callable[[str], str] = input,
    print_func: Callable[..., None] = print
) -> Tuple[float, float, float]:
    """
    Interactively prompts for RA, DEC, and Search Radius with validation loops.
    """
    while True:
        try:
            val = input_func("Enter RA  : ")
            ra = validate_ra(val)
            break
        except ValueError as e:
            print_func(f"Error: {e}. Please enter a valid RA in degrees [0, 360].")

    while True:
        try:
            val = input_func("Enter DEC : ")
            dec = validate_dec(val)
            break
        except ValueError as e:
            print_func(f"Error: {e}. Please enter a valid DEC in degrees [-90, 90].")

    while True:
        try:
            val = input_func("Enter search radius in arcmin [30]: ")
            radius = validate_radius(val, default=30.0)
            break
        except ValueError as e:
            print_func(f"Error: {e}. Please enter a radius between 0.1 and 120.0 arcmin.")

    return ra, dec, radius


def prompt_date_selection(
    dates: List[str],
    date_groups: Dict[str, List[SPHERExObservationModel]],
    input_func: Callable[[str], str] = input,
    print_func: Callable[..., None] = print
) -> List[int]:
    """
    Prompts the user to select at least two dates to compare, validating indices
    and verifying observations exist for the selected dates.
    """
    while True:
        print_func("\nSelect dates to compare")
        print_func("Example: 1,4\n")
        try:
            selection_str = input_func("> ")
            indices = parse_date_indices(selection_str, max_index=len(dates))
        except ValueError as e:
            print_func(f"Error: {e}\n")
            continue

        print_func("\nChecking selected observations...\n")
        all_valid = True
        for idx in indices:
            date_key = dates[idx - 1]
            obs_list = date_groups.get(date_key, [])
            if not obs_list:
                print_func(f"✗ Date {idx} ({date_key}): No matching observations found.")
                all_valid = False
            else:
                print_func(f"✓ Date {idx}: real observations found")

        if all_valid:
            return indices
        else:
            print_func("\nOne or more selected dates had no observations. Please select again.")


def display_selected_observations(
    selected_data: List[Tuple[str, SPHERExObservationModel]],
    print_func: Callable[..., None] = print
) -> None:
    """
    Formats and prints details of selected real SPHEREx observations.
    """
    print_func("\n================================")
    print_func("SELECTED OBSERVATIONS")
    print_func("================================\n")

    for i, (date_str, obs) in enumerate(selected_data, start=1):
        exposure_str = f"{obs.exposure_time_sec:.2f} s" if obs.exposure_time_sec is not None else "N/A"
        print_func(f"Observation {i}")
        print_func(f"Date           : {date_str}")
        print_func(f"UTC            : {obs.observation_time_utc or 'N/A'}")
        print_func(f"Observation ID : {obs.observation_id}")
        print_func(f"RA             : {obs.ra:.4f}")
        print_func(f"DEC            : {obs.dec:.4f}")
        print_func(f"Bandpass       : {obs.bandpass or 'N/A'}")
        print_func(f"Exposure       : {exposure_str}")
        print_func(f"Data type      : {obs.dataproduct_type or 'N/A'}")
        print_func(f"Access URL     : {obs.data_access_url or 'N/A'}")

        if i < len(selected_data):
            print_func("\n---\n")

    print_func("\n================================\n")
    print_func("✓ Selected real SPHEREx observations.")
    print_func("✓ These observations can now be passed to Step 2 for FITS cutout retrieval.")


def display_motion_analysis(
    result: Any,
    print_func: Callable[..., None] = print,
) -> None:
    """
    Formats and prints the Step 3 motion analysis results to the terminal.
    Displays epoch info, source counts, matched sources, candidates, warnings, and disclaimer.
    """
    print_func("\n================================")
    print_func("STEP 3: MOTION ANALYSIS")
    print_func("=======================\n")

    print_func("Observation 1:")
    print_func(f"Date: {result.observation_1.timestamp_utc or 'N/A'}")
    print_func(f"Observation ID: {result.observation_1.observation_id}")
    print_func(f"Bandpass: {result.observation_1.bandpass or 'Unknown'}")

    print_func("\nObservation 2:")
    print_func(f"Date: {result.observation_2.timestamp_utc or 'N/A'}")
    print_func(f"Observation ID: {result.observation_2.observation_id}")
    print_func(f"Bandpass: {result.observation_2.bandpass or 'Unknown'}")

    print_func("\nSource detection:")
    print_func(f"Epoch 1 sources: {result.source_statistics.sources_detected_epoch_1}")
    print_func(f"Epoch 2 sources: {result.source_statistics.sources_detected_epoch_2}")

    print_func("\nCross matching:")
    print_func(f"Matched sources: {result.source_statistics.matched_sources}")

    print_func(f"\nMoving-object candidates: {result.source_statistics.candidate_count}")

    # Display details for each matched source
    for idx, c in enumerate(result.candidates, start=1):
        print_func("\n---")
        print_func(f"\n## Source / Candidate {idx:03d}")
        print_func("\nEpoch 1:")
        print_func(f"Pixel position: ({c.position_epoch_1.x:.2f}, {c.position_epoch_1.y:.2f})")
        print_func(f"RA: {c.position_epoch_1.ra:.6f}")
        print_func(f"DEC: {c.position_epoch_1.dec:.6f}")

        print_func("\nEpoch 2:")
        print_func(f"Pixel position: ({c.position_epoch_2.x:.2f}, {c.position_epoch_2.y:.2f})")
        print_func(f"RA: {c.position_epoch_2.ra:.6f}")
        print_func(f"DEC: {c.position_epoch_2.dec:.6f}")

        print_func("\nAngular displacement:")
        print_func(f"{c.angular_displacement.arcsec:.4f} arcsec")
        print_func(f"{c.angular_displacement.arcmin:.6f} arcmin")

        print_func("\nElapsed time:")
        print_func(f"{result.time_difference.days:.4f} days")

        print_func("\nAverage angular speed:")
        print_func(f"{c.average_angular_speed.arcsec_per_day:.4f} arcsec/day")

        print_func("\nPosition angle:")
        print_func(f"{c.position_angle_deg:.2f} degrees")

        print_func("\nStatus:")
        print_func(f"{c.status}")

    # Candidates section
    candidates_only = [
        c for c in result.candidates if c.status == "moving-object-candidate"
    ]
    print_func("\n==================================================")
    print_func("CANDIDATES")
    print_func("==========")

    if candidates_only:
        for c in candidates_only:
            print_func("\n---")
            print_func("\n## MOVING-OBJECT CANDIDATE")
            print_func(f"Candidate ID: {c.candidate_id}")
            print_func(
                f"Position at epoch 1: RA {c.position_epoch_1.ra:.6f}, "
                f"DEC {c.position_epoch_1.dec:.6f} "
                f"(Pixel: {c.position_epoch_1.x:.2f}, {c.position_epoch_1.y:.2f})"
            )
            print_func(
                f"Position at epoch 2: RA {c.position_epoch_2.ra:.6f}, "
                f"DEC {c.position_epoch_2.dec:.6f} "
                f"(Pixel: {c.position_epoch_2.x:.2f}, {c.position_epoch_2.y:.2f})"
            )
            print_func(
                f"Angular displacement: {c.angular_displacement.arcsec:.4f} arcsec "
                f"({c.angular_displacement.arcmin:.6f} arcmin)"
            )
            print_func(f"Elapsed time: {result.time_difference.days:.4f} days")
            print_func(f"Average angular speed: {c.average_angular_speed.arcsec_per_day:.4f} arcsec/day")
            print_func(f"Position angle: {c.position_angle_deg:.2f} degrees ({c.direction_label})")
            print_func("Evidence:")
            for ev in c.evidence:
                print_func(f"* {ev}")
            if c.motion_trail_path:
                print_func(f"Motion trail: {c.motion_trail_path}")
            else:
                print_func("Motion trail: None generated")
    else:
        print_func("\nNo moving-object candidates were identified in this two-epoch comparison.")
        print_func("This is a valid scientific result.")

    # Warnings section
    if result.warnings:
        print_func("\n==================================================")
        print_func("WARNINGS")
        print_func("========")
        for w in result.warnings:
            print_func(f"\nWARNING:\n{w}")

    # Motion Trails section
    trail_paths = [c.motion_trail_path for c in result.candidates if c.motion_trail_path]
    if trail_paths:
        print_func("\n==================================================")
        print_func("MOTION TRAILS")
        print_func("=============")
        for tp in trail_paths:
            print_func(f"Motion trail: {tp}")

    # Mandatory scientific disclaimer
    if getattr(result, "scientific_disclaimer", None):
        print_func("\n==================================================")
        print_func(result.scientific_disclaimer)


def display_known_object_analysis(
    result: Any,
    obs1: Any,
    obs2: Any,
    detected_1: Optional[Any] = None,
    sep_1: Optional[float] = None,
    detected_2: Optional[Any] = None,
    sep_2: Optional[float] = None,
    val_plot_path: Optional[Path] = None,
    print_func: Callable[..., None] = print,
    target_result_1: Optional[Any] = None,
    target_result_2: Optional[Any] = None,
) -> None:
    """
    Formats and displays the Known Moving Object Validation report.
    Adheres strictly to scientific rules:
      - Uses real measured centroids from associate_target_source
      - Clearly distinguishes externally supplied predicted position vs independently measured image position
      - Reports prediction-to-measurement separation and detection status (DETECTED, NOT_DETECTED, AMBIGUOUS)
      - When one epoch is DETECTED and the other is NOT_DETECTED, explicitly reports:
        "Two-epoch motion not measurable because the target was not reliably detected in both epochs."
      - Does not calculate or fabricate target motion when target is not detected in both epochs.
    """
    from app.services.known_objects import (
        DetectionStatus,
        TargetAssociationResult,
    )

    if target_result_1 is None:
        if detected_1 is not None and sep_1 is not None and sep_1 <= 15.0:
            target_result_1 = TargetAssociationResult(
                target_name="3I/ATLAS",
                predicted_ra=obs1.comet_ra,
                predicted_dec=obs1.comet_dec,
                status=DetectionStatus.DETECTED,
                measured_ra=detected_1.ra,
                measured_dec=detected_1.dec,
                measured_x=detected_1.x,
                measured_y=detected_1.y,
                separation_arcsec=sep_1,
                snr=detected_1.snr,
                matched_source=detected_1,
                candidate_sources_in_tolerance=1,
                min_separation_arcsec=sep_1,
                evaluation_note="measured position is within the evaluated tolerance of the supplied prediction (consistent with supplied ephemeris)",
            )
        else:
            target_result_1 = TargetAssociationResult(
                target_name="3I/ATLAS",
                predicted_ra=obs1.comet_ra,
                predicted_dec=obs1.comet_dec,
                status=DetectionStatus.NOT_DETECTED,
                measured_ra=None,
                measured_dec=None,
                measured_x=None,
                measured_y=None,
                separation_arcsec=None,
                min_separation_arcsec=sep_1,
                evaluation_note="Object emission below stellar point-source detection threshold in this single exposure",
            )

    if target_result_2 is None:
        if detected_2 is not None and sep_2 is not None and sep_2 <= 15.0:
            target_result_2 = TargetAssociationResult(
                target_name="3I/ATLAS",
                predicted_ra=obs2.comet_ra,
                predicted_dec=obs2.comet_dec,
                status=DetectionStatus.DETECTED,
                measured_ra=detected_2.ra,
                measured_dec=detected_2.dec,
                measured_x=detected_2.x,
                measured_y=detected_2.y,
                separation_arcsec=sep_2,
                snr=detected_2.snr,
                matched_source=detected_2,
                candidate_sources_in_tolerance=1,
                min_separation_arcsec=sep_2,
                evaluation_note="measured position is within the evaluated tolerance of the supplied prediction (consistent with supplied ephemeris)",
            )
        else:
            target_result_2 = TargetAssociationResult(
                target_name="3I/ATLAS",
                predicted_ra=obs2.comet_ra,
                predicted_dec=obs2.comet_dec,
                status=DetectionStatus.NOT_DETECTED,
                measured_ra=None,
                measured_dec=None,
                measured_x=None,
                measured_y=None,
                separation_arcsec=None,
                min_separation_arcsec=sep_2,
                evaluation_note="Object emission below stellar point-source detection threshold in this single exposure",
            )

    res1 = target_result_1
    res2 = target_result_2

    print_func("\n================================")
    print_func("KNOWN OBJECT VALIDATION")
    print_func("================================\n")
    print_func("Target: 3I/ATLAS\n")
    print_func("Important:")
    print_func("This is a validation experiment using an externally supplied known-object")
    print_func("position from the official IRSA 3I/ATLAS observation table.\n")
    print_func("The measured motion below is independently derived from detected image")
    print_func("positions. The predicted coordinates are NOT treated as measured motion.\n")

    print_func("### Observation metadata\n")
    print_func("Epoch 1")
    print_func(f"Observation ID: {obs1.obs_id}")
    print_func(f"UTC: {obs1.observation_time_utc}")
    print_func(f"Detector: {obs1.spherex_detector} ({obs1.bandpass})")
    print_func(f"IRSA predicted RA/DEC: {obs1.comet_ra:.6f}, {obs1.comet_dec:.6f}\n")

    print_func("Epoch 2")
    print_func(f"Observation ID: {obs2.obs_id}")
    print_func(f"UTC: {obs2.observation_time_utc}")
    print_func(f"Detector: {obs2.spherex_detector} ({obs2.bandpass})")
    print_func(f"IRSA predicted RA/DEC: {obs2.comet_ra:.6f}, {obs2.comet_dec:.6f}\n")

    print_func("### Detection\n")
    if hasattr(result, "source_statistics") and result.source_statistics is not None:
        print_func(f"Epoch 1 detected sources: {result.source_statistics.sources_detected_epoch_1}")
        print_func(f"Epoch 2 detected sources: {result.source_statistics.sources_detected_epoch_2}")
        print_func(f"Matched sources: {result.source_statistics.matched_sources}\n")

    both_detected = (res1.status == DetectionStatus.DETECTED and res2.status == DetectionStatus.DETECTED)
    one_detected_one_not = (
        (res1.status == DetectionStatus.DETECTED and res2.status == DetectionStatus.NOT_DETECTED)
        or (res1.status == DetectionStatus.NOT_DETECTED and res2.status == DetectionStatus.DETECTED)
    )

    # Candidate summary / motion section
    print_func("\n==================================================")
    print_func("CANDIDATE SUMMARY")
    print_func("==================")

    if one_detected_one_not:
        print_func("\n---")
        print_func("\n## NO RELIABLE MOVING-OBJECT DETECTION\n")
        print_func("Two-epoch motion not measurable because the target was not reliably detected in both epochs.")
    elif both_detected:
        # Display measured target motion between both epochs if available
        candidates_only = [
            c for c in getattr(result, "candidates", [])
            if getattr(c, "status", "") == "moving-object-candidate"
        ]
        if candidates_only:
            for c in candidates_only:
                print_func("\n---")
                print_func("\n## MOVING-OBJECT CANDIDATE")
                print_func(f"Candidate ID: {c.candidate_id}")
                print_func(f"Measured displacement: {c.angular_displacement.arcsec:.4f} arcsec")
                print_func(f"Angular speed: {c.average_angular_speed.arcsec_per_day:.4f} arcsec/day")
                print_func(f"Detection confidence: {c.quality.confidence}")
                if getattr(c, "motion_trail_path", None):
                    print_func(f"Motion trail: {c.motion_trail_path}")
        else:
            print_func("\n---")
            print_func("\n## TARGET DETECTED IN BOTH EPOCHS")
            print_func("Both epochs detected the target within tolerance.")
    else:
        print_func("\n---")
        print_func("\n## NO RELIABLE MOVING-OBJECT DETECTION\n")
        print_func("The known object was not sufficiently detected in the selected")
        print_func("SPHEREx images to independently measure its motion.")

    # Prediction vs Measurement
    print_func("\n==================================================")
    print_func("PREDICTED VS MEASURED COMPARISON")
    print_func("==================================================\n")
    print_func("Prediction vs measurement\n")

    print_func("Epoch 1:")
    print_func(f"Externally supplied predicted position → RA {res1.predicted_ra:.6f}, DEC {res1.predicted_dec:.6f}")
    if res1.status == DetectionStatus.DETECTED:
        pix_str = f" (Pixel: {res1.measured_x:.2f}, {res1.measured_y:.2f}, SNR: {res1.snr:.1f})" if res1.measured_x is not None else ""
        print_func(f"Independently measured image position  → RA {res1.measured_ra:.6f}, DEC {res1.measured_dec:.6f}{pix_str}")
        sep_pix_str = f" ({res1.pixel_separation:.2f} pixels)" if res1.pixel_separation is not None else ""
        print_func(f"Prediction-to-measurement separation: Separation → {res1.separation_arcsec:.2f} arcsec{sep_pix_str}")
        print_func(f"Detection status                       → {res1.status.value}")
        print_func("Evaluation                             → measured position is within the evaluated tolerance of the supplied prediction (consistent with supplied ephemeris)")
    elif res1.status == DetectionStatus.AMBIGUOUS:
        pix_str = f" (Pixel: {res1.measured_x:.2f}, {res1.measured_y:.2f}, SNR: {res1.snr:.1f})" if res1.measured_x is not None else ""
        print_func(f"Independently measured image position  → RA {res1.measured_ra:.6f}, DEC {res1.measured_dec:.6f}{pix_str}")
        print_func(f"Prediction-to-measurement separation: Separation → {res1.separation_arcsec:.2f} arcsec")
        print_func(f"Detection status                       → {res1.status.value}")
        print_func(f"Evaluation                             → {res1.evaluation_note}")
    else:
        print_func("Independently measured image position  → Target not reliably detected above threshold")
        print_func("Measured  → Target not reliably detected above threshold")
        print_func(f"Detection status                       → {res1.status.value}")
        print_func("Evaluation                             → Object emission below stellar point-source detection threshold in this single exposure")

    print_func("\nEpoch 2:")
    print_func(f"Externally supplied predicted position → RA {res2.predicted_ra:.6f}, DEC {res2.predicted_dec:.6f}")
    if res2.status == DetectionStatus.DETECTED:
        pix_str = f" (Pixel: {res2.measured_x:.2f}, {res2.measured_y:.2f}, SNR: {res2.snr:.1f})" if res2.measured_x is not None else ""
        print_func(f"Independently measured image position  → RA {res2.measured_ra:.6f}, DEC {res2.measured_dec:.6f}{pix_str}")
        sep_pix_str = f" ({res2.pixel_separation:.2f} pixels)" if res2.pixel_separation is not None else ""
        print_func(f"Prediction-to-measurement separation: Separation → {res2.separation_arcsec:.2f} arcsec{sep_pix_str}")
        print_func(f"Detection status                       → {res2.status.value}")
        print_func("Evaluation                             → measured position is within the evaluated tolerance of the supplied prediction (consistent with supplied ephemeris)")
    elif res2.status == DetectionStatus.AMBIGUOUS:
        pix_str = f" (Pixel: {res2.measured_x:.2f}, {res2.measured_y:.2f}, SNR: {res2.snr:.1f})" if res2.measured_x is not None else ""
        print_func(f"Independently measured image position  → RA {res2.measured_ra:.6f}, DEC {res2.measured_dec:.6f}{pix_str}")
        print_func(f"Prediction-to-measurement separation: Separation → {res2.separation_arcsec:.2f} arcsec")
        print_func(f"Detection status                       → {res2.status.value}")
        print_func(f"Evaluation                             → {res2.evaluation_note}")
    else:
        print_func("Independently measured image position  → Target not reliably detected above threshold")
        print_func("Measured  → Target not reliably detected above threshold")
        print_func(f"Detection status                       → {res2.status.value}")
        print_func("Evaluation                             → Object emission below stellar point-source detection threshold in this single exposure")

    if val_plot_path:
        print_func("\n==================================================")
        print_func("VISUALIZATION")
        print_func("=============")
        print_func(f"Validation comparison plot: {val_plot_path}")

    # Warnings
    if getattr(result, "warnings", None):
        print_func("\n==================================================")
        print_func("WARNINGS")
        print_func("========")
        for w in result.warnings:
            print_func(f"\nWARNING:\n{w}")

    # Mandatory scientific disclaimer
    if getattr(result, "scientific_disclaimer", None):
        print_func("\n==================================================")
        print_func(result.scientific_disclaimer)


def run_known_object_cli(
    input_func: Callable[[str], str] = input,
    print_func: Callable[..., None] = print,
    motion_service: Optional[Callable] = None,
    pair_service: Optional[Callable] = None,
) -> bool:
    """
    Executes the Known Moving Object Test mode for 3I/ATLAS.
    Uses the official NASA/IPAC IRSA 3I/ATLAS observation table.
    """
    from app.services.known_objects import (
        get_known_object_pair,
        to_spherex_observation,
        associate_target_source,
        DetectionStatus,
        TargetAssociationResult,
        generate_known_object_visualization,
        KnownObjectError,
    )
    from app.services.cutout_service import fetch_spherex_cutout
    from app.services.fits_service import inspect_fits_cutout, generate_preview
    from app.services.source_detection import load_science_image, detect_sources
    from app.models.motion import MotionAnalysisRequest
    from app.config import settings

    print_func("\n================================")
    print_func("KNOWN MOVING OBJECT TEST")
    print_func("================================\n")
    print_func("Object: 3I/ATLAS\n")
    print_func("Source:")
    print_func("Official NASA/IPAC IRSA SPHEREx 3I/ATLAS observation table\n")

    cache_dir = Path(settings.CACHE_DIR)
    previews_dir = cache_dir / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)

    try:
        if pair_service is not None:
            obs1, obs2 = pair_service()
        else:
            obs1, obs2 = get_known_object_pair(cache_dir=cache_dir)
    except KnownObjectError as e:
        print_func(f"✗ Failed to load 3I/ATLAS observations: {e}")
        return False

    print_func("Selected observations:\n")
    print_func(f"1. {obs1.obs_id}")
    print_func(f"   Date: {obs1.observation_time_utc[:10]}")
    print_func(f"   Time: {obs1.observation_time_utc[11:16]}")
    print_func(f"   Detector: {obs1.spherex_detector}")
    print_func(f"   Predicted RA: {obs1.comet_ra:.9f}")
    print_func(f"   Predicted DEC: {obs1.comet_dec:.9f}\n")

    print_func(f"2. {obs2.obs_id}")
    print_func(f"   Date: {obs2.observation_time_utc[:10]}")
    print_func(f"   Time: {obs2.observation_time_utc[11:16]}")
    print_func(f"   Detector: {obs2.spherex_detector}")
    print_func(f"   Predicted RA: {obs2.comet_ra:.9f}")
    print_func(f"   Predicted DEC: {obs2.comet_dec:.9f}\n")

    downloaded = []
    for idx, obs in enumerate([obs1, obs2], start=1):
        print_func(f"Processing Observation {idx} ({obs.obs_id}, Date: {obs.observation_time_utc[:10]})...")
        print_func("Resolving SPHEREx image...")
        sph_obs = to_spherex_observation(obs)
        try:
            fits_path, cached = fetch_spherex_cutout(
                observation=sph_obs,
                ra=obs.comet_ra,
                dec=obs.comet_dec,
                size_deg=0.05,
                cache_dir=cache_dir,
            )
            print_func("✓ Image resource resolved")
            print_func(f"✓ Cutout {'loaded from cache' if cached else 'downloaded'}: {fits_path.name}")
            print_func("Opening FITS...")
            fits_info = inspect_fits_cutout(fits_path, center_ra=obs.comet_ra, center_dec=obs.comet_dec)
            print_func("✓ Valid FITS")
            print_func(f"  Science HDU: {fits_info['science_name']} (index {fits_info['science_index']}), Shape: {fits_info['image_shape']}")
            print_func("Inspecting WCS...")
            if fits_info["wcs_available"]:
                print_func(f"✓ WCS available: {fits_info['wcs_summary']}")
            else:
                print_func("✗ WCS not available")

            preview_path = previews_dir / f"{fits_path.stem}_preview.png"
            generate_preview(
                fits_path=fits_path,
                output_png_path=preview_path,
                center_ra=obs.comet_ra,
                center_dec=obs.comet_dec,
                title=f"3I/ATLAS {obs.obs_id} ({obs.bandpass})"
            )
            print_func(f"Preview generated: cache/previews/{preview_path.name}\n")
            downloaded.append((obs, fits_path))
        except Exception as e:
            print_func(f"✗ Cutout error: {e}")
            return False

    if len(downloaded) != 2:
        print_func("✗ Error: Could not retrieve both cutouts for validation.")
        return False

    (obs1, p1), (obs2, p2) = downloaded

    # Run Step 3 Motion Analysis
    if motion_service is None:
        from app.services.motion_analysis import run_motion_analysis
        motion_service = run_motion_analysis

    # Detection evaluation against predicted positions using associate_target_source
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
        logger.warning("Could not evaluate epoch 1 detection: %s", e)
        target_res_1 = TargetAssociationResult(
            target_name="3I/ATLAS",
            predicted_ra=obs1.comet_ra,
            predicted_dec=obs1.comet_dec,
            status=DetectionStatus.NOT_DETECTED,
            evaluation_note=f"Error evaluating epoch 1: {e}",
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
        logger.warning("Could not evaluate epoch 2 detection: %s", e)
        target_res_2 = TargetAssociationResult(
            target_name="3I/ATLAS",
            predicted_ra=obs2.comet_ra,
            predicted_dec=obs2.comet_dec,
            status=DetectionStatus.NOT_DETECTED,
            evaluation_note=f"Error evaluating epoch 2: {e}",
        )
        sources_2 = []

    det1 = target_res_1.matched_source
    sep1 = target_res_1.separation_arcsec or target_res_1.min_separation_arcsec
    det2 = target_res_2.matched_source
    sep2 = target_res_2.separation_arcsec or target_res_2.min_separation_arcsec

    both_detected = (
        target_res_1.status == DetectionStatus.DETECTED
        and target_res_2.status == DetectionStatus.DETECTED
    )
    one_detected_one_not = (
        (target_res_1.status == DetectionStatus.DETECTED and target_res_2.status == DetectionStatus.NOT_DETECTED)
        or (target_res_1.status == DetectionStatus.NOT_DETECTED and target_res_2.status == DetectionStatus.DETECTED)
    )

    if both_detected:
        if motion_service is None:
            from app.services.motion_analysis import run_motion_analysis
            motion_service = run_motion_analysis

        req = MotionAnalysisRequest(
            fits_path_1=str(p1),
            fits_path_2=str(p2),
            observation_id_1=obs1.obs_id,
            observation_id_2=obs2.obs_id,
            ra=obs1.comet_ra,
            dec=obs1.comet_dec,
            ra_2=obs2.comet_ra,
            dec_2=obs2.comet_dec,
            timestamp_utc_1=obs1.observation_time_utc,
            timestamp_utc_2=obs2.observation_time_utc,
            timestamp_mjd_1=obs1.observation_time_mjd,
            timestamp_mjd_2=obs2.observation_time_mjd,
            bandpass_1=obs1.bandpass,
            bandpass_2=obs2.bandpass,
        )
        try:
            analysis_result = motion_service(req)
        except Exception as e:
            print_func(f"\n✗ Motion analysis error: {e}")
            return False
    else:
        # Target not detected in both epochs: do NOT calculate or fabricate target motion!
        from app.models.motion import MotionAnalysisResult, SourceStatistics, TimeDifference

        time_diff_days = abs(obs2.observation_time_mjd - obs1.observation_time_mjd)
        time_diff_sec = time_diff_days * 86400.0
        time_diff_hours = time_diff_sec / 3600.0
        warnings_list = []
        if one_detected_one_not:
            warnings_list.append("Two-epoch motion not measurable because the target was not reliably detected in both epochs.")
        else:
            warnings_list.append("Target was not reliably detected in either epoch.")

        import uuid
        from app.models.motion import EpochInfo, MotionAnalysisResult, SourceStatistics, TimeDifference

        epoch_info_1 = EpochInfo(
            observation_id=obs1.obs_id,
            timestamp_utc=obs1.observation_time_utc,
            timestamp_mjd=obs1.observation_time_mjd,
            ra_center=obs1.comet_ra,
            dec_center=obs1.comet_dec,
            bandpass=obs1.bandpass,
            fits_path=str(p1),
            image_shape=list(d1.shape) if d1 is not None else [0, 0],
            wcs_available=w1 is not None,
            wcs_projection=w1.to_header().get("CTYPE1", "WCS") if w1 is not None else None,
            sources_detected=len(sources_1),
        )
        epoch_info_2 = EpochInfo(
            observation_id=obs2.obs_id,
            timestamp_utc=obs2.observation_time_utc,
            timestamp_mjd=obs2.observation_time_mjd,
            ra_center=obs2.comet_ra,
            dec_center=obs2.comet_dec,
            bandpass=obs2.bandpass,
            fits_path=str(p2),
            image_shape=list(d2.shape) if d2 is not None else [0, 0],
            wcs_available=w2 is not None,
            wcs_projection=w2.to_header().get("CTYPE1", "WCS") if w2 is not None else None,
            sources_detected=len(sources_2),
        )

        analysis_result = MotionAnalysisResult(
            analysis_id=str(uuid.uuid4()),
            observation_1=epoch_info_1,
            observation_2=epoch_info_2,
            time_difference=TimeDifference(days=time_diff_days, hours=time_diff_hours, seconds=time_diff_sec),
            source_statistics=SourceStatistics(
                sources_detected_epoch_1=len(sources_1),
                sources_detected_epoch_2=len(sources_2),
                matched_sources=0,
                stationary_count=0,
                possible_motion_count=0,
                candidate_count=0,
                unmatched_epoch_1=len(sources_1),
                unmatched_epoch_2=len(sources_2),
            ),
            candidates=[],
            warnings=warnings_list,
        )

    # Generate validation plot
    val_plot_path = previews_dir / "3I_ATLAS_validation.png"
    try:
        generate_known_object_visualization(
            fits_path_1=p1,
            fits_path_2=p2,
            pred_ra_1=obs1.comet_ra,
            pred_dec_1=obs1.comet_dec,
            pred_ra_2=obs2.comet_ra,
            pred_dec_2=obs2.comet_dec,
            detected_1=det1,
            detected_2=det2,
            output_png_path=val_plot_path,
            title="3I/ATLAS SPHEREx Validation (2025-08-07)"
        )
    except Exception as e:
        logger.warning("Could not generate validation plot: %s", e)

    # Display Known Object Report
    display_known_object_analysis(
        result=analysis_result,
        obs1=obs1,
        obs2=obs2,
        detected_1=det1,
        sep_1=sep1,
        detected_2=det2,
        sep_2=sep2,
        val_plot_path=val_plot_path if val_plot_path.exists() else None,
        print_func=print_func,
        target_result_1=target_res_1,
        target_result_2=target_res_2,
    )
    return True


def run_cli(
    input_func: Callable[[str], str] = input,
    print_func: Callable[..., None] = print,
    search_service: Callable[..., List[SPHERExObservationModel]] = search_spherex_observations,
    motion_service: Optional[Callable] = None,
    pair_service: Optional[Callable] = None,
) -> Optional[List[Tuple[str, SPHERExObservationModel, List[SPHERExObservationModel]]]]:
    """
    Main interactive CLI workflow.
    Supports:
      1. Normal SPHEREx Search (RA, DEC, radius, date selection, cutout, motion analysis)
      2. Known Moving Object Test — 3I/ATLAS (Official IRSA ephemeris validation)
    """
    print_func("# SPHEREx Moving Object Explorer\n")
    print_func("1. Normal SPHEREx Search")
    print_func("2. Known Moving Object Test — 3I/ATLAS\n")

    mode_raw = input_func("Select mode [1/2] (default: 1): ").strip()

    if mode_raw == "2":
        run_known_object_cli(
            input_func=input_func,
            print_func=print_func,
            motion_service=motion_service,
            pair_service=pair_service,
        )
        return []

    # If user entered coordinates directly (e.g. from an automated test that passes RA first)
    ra_val = None
    if mode_raw not in ("", "1"):
        try:
            ra_val = validate_ra(mode_raw)
        except Exception:
            pass

    if ra_val is not None:
        ra = ra_val
        while True:
            try:
                val = input_func("Enter DEC : ")
                dec = validate_dec(val)
                break
            except ValueError as e:
                print_func(f"Error: {e}. Please enter a valid DEC in degrees [-90, 90].")
        while True:
            try:
                val = input_func("Enter search radius in arcmin [30]: ")
                radius = validate_radius(val, default=30.0)
                break
            except ValueError as e:
                print_func(f"Error: {e}. Please enter a radius between 0.1 and 120.0 arcmin.")
    else:
        ra, dec, radius = prompt_coordinates(input_func=input_func, print_func=print_func)

    observations = None
    while True:
        print_func(f"\nSearching real SPHEREx observations (RA={ra}, DEC={dec}, Radius={radius} arcmin)...\n")
        try:
            observations = search_service(ra=ra, dec=dec, radius_arcmin=radius)
            break
        except IRSAError as e:
            print_func(f"\nError querying NASA/IRSA service: {e}")
            retry_choice = input_func("Would you like to retry the search? [Y/n]: ").strip().lower()
            if retry_choice in ("", "y", "yes"):
                continue
            return None
        except Exception as e:
            print_func(f"\nUnexpected error: {e}")
            return None

    if not observations:
        print_func("No real SPHEREx observations found for these coordinates and search radius.")
        return None

    print_func(f"✓ Found {len(observations)} real SPHEREx observations.\n")

    # Group observations by calendar date
    date_groups = group_observations_by_date(observations)
    dates = list(date_groups.keys())

    if len(dates) < 2:
        print_func(
            f"Only 1 observation date found ({dates[0] if dates else 'None'}). "
            "Temporal comparison requires at least 2 distinct dates."
        )
        return None

    print_func("Available observation dates:\n")
    for idx, d in enumerate(dates, start=1):
        count = len(date_groups[d])
        obs_label = "observation" if count == 1 else "observations"
        print_func(f"{idx}. {d:<13} {count} {obs_label}")

    selected_indices = prompt_date_selection(
        dates=dates,
        date_groups=date_groups,
        input_func=input_func,
        print_func=print_func
    )

    selected_results: List[Tuple[str, SPHERExObservationModel, List[SPHERExObservationModel]]] = []
    display_items: List[Tuple[str, SPHERExObservationModel]] = []

    for idx in selected_indices:
        date_str = dates[idx - 1]
        all_obs = date_groups[date_str]
        chosen_obs = select_representative_observation(all_obs)
        selected_results.append((date_str, chosen_obs, all_obs))
        display_items.append((date_str, chosen_obs))

    display_selected_observations(display_items, print_func=print_func)

    # Step 2: Optional Cutout Retrieval
    print_func("")
    cutout_choice = input_func("Would you like to retrieve image cutouts? [y/N]: ").strip().lower()
    downloaded_cutouts: List[Tuple[str, SPHERExObservationModel, Any]] = []
    if cutout_choice in ("y", "yes"):
        from pathlib import Path
        from app.services.cutout_service import fetch_spherex_cutout
        from app.services.fits_service import inspect_fits_cutout, generate_preview
        from app.config import settings

        cache_dir = Path(settings.CACHE_DIR)
        previews_dir = cache_dir / "previews"

        for idx, (date_str, chosen_obs) in enumerate(display_items, start=1):
            print_func(f"\nProcessing Observation {idx} ({chosen_obs.observation_id}, Date: {date_str})...")
            print_func("Resolving SPHEREx image...")
            try:
                fits_path, cached = fetch_spherex_cutout(
                    observation=chosen_obs,
                    ra=ra,
                    dec=dec,
                    size_deg=0.05,
                    cache_dir=cache_dir
                )
                print_func("✓ Image resource resolved")
                print_func(f"✓ Cutout {'loaded from cache' if cached else 'downloaded'}: {fits_path.name}")
                print_func("Opening FITS...")
                fits_info = inspect_fits_cutout(fits_path, center_ra=ra, center_dec=dec)
                print_func("✓ Valid FITS")
                print_func(f"  Science HDU: {fits_info['science_name']} (index {fits_info['science_index']}), Shape: {fits_info['image_shape']}")
                print_func("Inspecting WCS...")
                if fits_info["wcs_available"]:
                    print_func(f"✓ WCS available: {fits_info['wcs_summary']}")
                else:
                    print_func("✗ WCS not available")

                # Generate preview
                preview_path = previews_dir / f"{fits_path.stem}_preview.png"
                generate_preview(
                    fits_path=fits_path,
                    output_png_path=preview_path,
                    center_ra=ra,
                    center_dec=dec,
                    title=f"SPHEREx {chosen_obs.observation_id} ({chosen_obs.bandpass or 'Image'})"
                )
                print_func(f"Preview generated: cache/previews/{preview_path.name}")
                downloaded_cutouts.append((date_str, chosen_obs, fits_path))
            except Exception as e:
                print_func(f"✗ Cutout error: {e}")

            if idx < len(display_items):
                next_choice = input_func("\nProceed to retrieve next observation cutout? [Y/n]: ").strip().lower()
                if next_choice not in ("", "y", "yes"):
                    print_func("Skipping remaining cutouts.")
                    break

        # Step 3: Motion Analysis (automatically invoked when exactly 2 cutouts are downloaded)
        if len(downloaded_cutouts) == 2:
            (d1, obs1, p1), (d2, obs2, p2) = downloaded_cutouts
            from app.models.motion import MotionAnalysisRequest
            if motion_service is None:
                from app.services.motion_analysis import run_motion_analysis
                motion_service = run_motion_analysis

            req = MotionAnalysisRequest(
                fits_path_1=str(p1),
                fits_path_2=str(p2),
                observation_id_1=obs1.observation_id,
                observation_id_2=obs2.observation_id,
                ra=ra,
                dec=dec,
                timestamp_utc_1=obs1.observation_time_utc or d1,
                timestamp_utc_2=obs2.observation_time_utc or d2,
                timestamp_mjd_1=obs1.observation_time_mjd,
                timestamp_mjd_2=obs2.observation_time_mjd,
                bandpass_1=obs1.bandpass,
                bandpass_2=obs2.bandpass,
            )

            try:
                analysis_result = motion_service(req)
                display_motion_analysis(analysis_result, print_func=print_func)
            except Exception as e:
                print_func(f"\n✗ Motion analysis error: {e}")

    return selected_results


def main() -> None:
    """Entry point for python -m app.cli"""
    try:
        run_cli()
    except (KeyboardInterrupt, EOFError):
        print("\nOperation cancelled by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
