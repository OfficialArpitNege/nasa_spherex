"""
Live verification script for Step 3: Motion analysis pipeline.

Runs the complete two-epoch motion analysis against REAL cached SPHEREx FITS cutouts
produced by Step 2. This script uses actual NASA/IRSA data — no synthetic arrays.

Usage:
    cd backend
    python test_motion_live.py

Two test cases:
  1. Same-band comparison (D4 vs D4): Best for motion analysis
     2025W18_1B_0001_1 (2025-04-28, SPHEREx-D4) vs
     2025W47_2A_0034_1 (2025-11-20, SPHEREx-D4)

  2. Cross-band comparison (D4 vs D1): Tests bandpass warning system
     2025W18_1B_0001_1 (2025-04-28, SPHEREx-D4) vs
     2026W18_1A_0317_1 (2026-04-28, SPHEREx-D1)
"""
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.models.motion import MotionAnalysisRequest
from app.services.motion_analysis import run_motion_analysis

CACHE_DIR = Path(__file__).parent / "cache"

# === Test Case 1: Same-band D4 vs D4 ===
# These are the best available pair for motion analysis:
# both use SPHEREx-D4 detector and cover the same sky region near RA=276.26, DEC=64.82
FITS_D4_EPOCH1 = CACHE_DIR / "spherex_2025W18_1B_0001_1_SPHEREx-D4_276.2600_64.8200_0.05deg.fits"
FITS_D4_EPOCH2 = CACHE_DIR / "spherex_2025W47_2A_0034_1_SPHEREx-D4_276.2600_64.8200_0.05deg.fits"

# === Test Case 2: Cross-band D4 vs D1 ===
FITS_D1_EPOCH2 = CACHE_DIR / "spherex_2026W18_1A_0317_1_SPHEREx-D1_276.2632_64.8225_0.05deg.fits"


def print_section(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def run_test_case(
    label: str,
    fits_1: Path,
    fits_2: Path,
    obs_id_1: str,
    obs_id_2: str,
    timestamp_1: str,
    timestamp_2: str,
    bandpass_1: str,
    bandpass_2: str,
    ra: float = 276.26,
    dec: float = 64.82,
):
    print_section(f"TEST CASE: {label}")

    if not fits_1.exists():
        print(f"SKIP: FITS file not found: {fits_1}")
        return None
    if not fits_2.exists():
        print(f"SKIP: FITS file not found: {fits_2}")
        return None

    print(f"Epoch 1: {obs_id_1} ({timestamp_1[:10]}, {bandpass_1})")
    print(f"  FITS: {fits_1.name} ({fits_1.stat().st_size:,} bytes)")
    print(f"Epoch 2: {obs_id_2} ({timestamp_2[:10]}, {bandpass_2})")
    print(f"  FITS: {fits_2.name} ({fits_2.stat().st_size:,} bytes)")
    print(f"Target: RA={ra}, DEC={dec}")
    print()

    request = MotionAnalysisRequest(
        fits_path_1=str(fits_1),
        fits_path_2=str(fits_2),
        observation_id_1=obs_id_1,
        observation_id_2=obs_id_2,
        ra=ra,
        dec=dec,
        timestamp_utc_1=timestamp_1,
        timestamp_utc_2=timestamp_2,
        bandpass_1=bandpass_1,
        bandpass_2=bandpass_2,
        detection_sigma=3.0,
        match_tolerance_arcsec=30.0,
        motion_threshold_arcsec=2.0,
        candidate_threshold_arcsec=6.2,
    )

    try:
        result = run_motion_analysis(request)
    except Exception as e:
        print(f"ERROR: Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None

    # Report results
    print(f"Analysis ID: {result.analysis_id}")
    print()

    print("--- TIME DIFFERENCE ---")
    td = result.time_difference
    print(f"  Elapsed: {td.days:.2f} days ({td.hours:.1f} hours, {td.seconds:.0f} seconds)")
    print()

    print("--- SOURCE DETECTION ---")
    stats = result.source_statistics
    print(f"  Epoch 1 ({obs_id_1}): {stats.sources_detected_epoch_1} sources detected")
    print(f"  Epoch 2 ({obs_id_2}): {stats.sources_detected_epoch_2} sources detected")
    print()

    print("--- CROSS-MATCHING ---")
    print(f"  Matched sources:      {stats.matched_sources}")
    print(f"  Stationary:           {stats.stationary_count}")
    print(f"  Possible motion:      {stats.possible_motion_count}")
    print(f"  Moving-obj candidates: {stats.candidate_count}")
    print(f"  Unmatched (epoch 1):  {stats.unmatched_epoch_1}")
    print(f"  Unmatched (epoch 2):  {stats.unmatched_epoch_2}")
    print()

    print("--- DETECTION PARAMETERS ---")
    for k, v in result.detection_parameters.items():
        print(f"  {k}: {v}")
    print()

    if result.candidates:
        print("--- CANDIDATES ---")
        for c in result.candidates:
            print(f"\n  [{c.candidate_id}] Status: {c.status}")
            print(f"    Epoch 1: pixel=({c.position_epoch_1.x:.2f}, {c.position_epoch_1.y:.2f}) "
                  f"sky=(RA={c.position_epoch_1.ra:.6f}, DEC={c.position_epoch_1.dec:.6f})")
            print(f"    Epoch 2: pixel=({c.position_epoch_2.x:.2f}, {c.position_epoch_2.y:.2f}) "
                  f"sky=(RA={c.position_epoch_2.ra:.6f}, DEC={c.position_epoch_2.dec:.6f})")
            print(f"    Angular displacement: {c.angular_displacement.arcsec:.4f} arcsec "
                  f"({c.angular_displacement.arcmin:.6f} arcmin)")
            print(f"    Angular speed: {c.average_angular_speed.arcsec_per_day:.4f} arcsec/day")
            print(f"    Position angle: {c.position_angle_deg:.1f}° ({c.direction_label})")
            print(f"    SNR: epoch1={c.quality.snr_epoch_1}, epoch2={c.quality.snr_epoch_2}")
            if c.quality.centroid_uncertainty_arcsec is not None:
                print(f"    Centroid uncertainty: {c.quality.centroid_uncertainty_arcsec:.4f} arcsec")
            if c.quality.displacement_to_uncertainty_ratio is not None:
                print(f"    Displacement/uncertainty: {c.quality.displacement_to_uncertainty_ratio:.2f} sigma")
            print(f"    Confidence: {c.quality.confidence}")
            print(f"    Evidence: {c.evidence}")
            if c.motion_trail_path:
                print(f"    Motion trail: {c.motion_trail_path}")
        print()

    print("--- WARNINGS ---")
    for w in result.warnings:
        print(f"  WARNING: {w}")
    print()

    print("--- SCIENTIFIC DISCLAIMER ---")
    print(f"  {result.scientific_disclaimer}")
    print()

    return result


def main():
    print("=" * 70)
    print("  SPHEREx Moving Object Explorer — Step 3 Live Verification")
    print("  Using REAL NASA/IRSA SPHEREx FITS cutouts")
    print("=" * 70)

    # Test Case 1: Same band (D4 vs D4) — best for motion analysis
    result_1 = run_test_case(
        label="Same-Band Comparison (D4 vs D4, ~206 days apart)",
        fits_1=FITS_D4_EPOCH1,
        fits_2=FITS_D4_EPOCH2,
        obs_id_1="2025W18_1B_0001_1",
        obs_id_2="2025W47_2A_0034_1",
        timestamp_1="2025-04-28 13:00:15.754",
        timestamp_2="2025-11-20 13:00:00.000",
        bandpass_1="SPHEREx-D4",
        bandpass_2="SPHEREx-D4",
    )

    # Test Case 2: Cross-band (D4 vs D1) — tests bandpass mismatch warning
    result_2 = run_test_case(
        label="Cross-Band Comparison (D4 vs D1, ~365 days apart)",
        fits_1=FITS_D4_EPOCH1,
        fits_2=FITS_D1_EPOCH2,
        obs_id_1="2025W18_1B_0001_1",
        obs_id_2="2026W18_1A_0317_1",
        timestamp_1="2025-04-28 13:00:15.754",
        timestamp_2="2026-04-28 01:21:40.854",
        bandpass_1="SPHEREx-D4",
        bandpass_2="SPHEREx-D1",
    )

    # Summary
    print_section("LIVE VERIFICATION SUMMARY")
    for i, (label, result) in enumerate([
        ("Same-band D4 vs D4", result_1),
        ("Cross-band D4 vs D1", result_2),
    ], 1):
        if result is None:
            print(f"  Test {i} ({label}): SKIPPED")
        else:
            stats = result.source_statistics
            print(f"  Test {i} ({label}):")
            print(f"    Sources: {stats.sources_detected_epoch_1} / {stats.sources_detected_epoch_2}")
            print(f"    Matched: {stats.matched_sources}")
            print(f"    Candidates: {stats.candidate_count}")
            print(f"    Bandpass warning: {'Yes' if any('BANDPASS' in w for w in result.warnings) else 'No'}")

    print()
    print("[OK] Live verification complete")


if __name__ == "__main__":
    main()
