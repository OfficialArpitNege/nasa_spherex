#!/usr/bin/env python3
"""
Live verification script for SPHEREx Cutout Service and FITS inspection.
Tests both real observations:
1. 2025W18_1B_0001_1 (SPHEREx-D4)
2. 2026W18_1A_0317_1 (SPHEREx-D1)
"""

import sys
from pathlib import Path
from astropy.io import fits

from app.models.search import SPHERExObservationModel
from app.services.cutout_service import fetch_spherex_cutout, resolve_datalink_fits_url
from app.services.fits_service import generate_preview, inspect_fits_cutout


def verify_observation_cutout(obs: SPHERExObservationModel, ra: float, dec: float, size_deg: float = 0.05):
    print("=" * 65)
    print(f"  VERIFYING REAL SPHEREx OBSERVATION: {obs.observation_id}")
    print(f"  Bandpass: {obs.bandpass} | Coordinates: ({ra:.4f}, {dec:.4f}) | Size: {size_deg} deg")
    print("=" * 65)

    print(f"Step 1: Resolving Datalink...")
    print(f"  Datalink URL: {obs.data_access_url}")
    fits_url = resolve_datalink_fits_url(obs.data_access_url)
    print(f"  [SUCCESS] Resolved FITS URL: {fits_url}")

    print(f"\nStep 2: Requesting Cutout from IRSA Cutout Service...")
    fits_path, cached = fetch_spherex_cutout(
        observation=obs,
        ra=ra,
        dec=dec,
        size_deg=size_deg
    )
    status_str = "Loaded from local cache" if cached else "Downloaded from NASA/IRSA"
    print(f"  [SUCCESS] Cutout FITS ({status_str}): {fits_path.name}")
    print(f"  File Size: {fits_path.stat().st_size:,} bytes")

    print(f"\nStep 3: Inspecting FITS Structure & HDUs...")
    with fits.open(fits_path) as hdul:
        print("  --- HDUL.INFO() ---")
        hdul.info()
        print("  -------------------")

    fits_info = inspect_fits_cutout(fits_path, center_ra=ra, center_dec=dec)
    print(f"  Science HDU Name  : {fits_info['science_name']} (index {fits_info['science_index']})")
    print(f"  Science Image Shape: {fits_info['image_shape']} [height, width]")
    print(f"  WCS Available      : {fits_info['wcs_available']}")
    if fits_info['wcs_available']:
        print(f"  WCS Summary        : {fits_info['wcs_summary']}")
        print(f"  Target Pixel Coords: {fits_info['target_pixel_coords']}")
    else:
        print(f"  [WARNING] WCS was not available.")

    print(f"\nStep 4: Generating Astronomical Image Preview PNG...")
    previews_dir = fits_path.parent / "previews"
    preview_path = previews_dir / f"{fits_path.stem}_preview.png"
    generate_preview(
        fits_path=fits_path,
        output_png_path=preview_path,
        center_ra=ra,
        center_dec=dec,
        title=f"SPHEREx {obs.observation_id} ({obs.bandpass})"
    )
    print(f"  [SUCCESS] Preview saved to: {preview_path}")
    print(f"  Preview File Size: {preview_path.stat().st_size:,} bytes")
    assert preview_path.exists() and preview_path.stat().st_size > 1000

    print(f"\n[PASSED] Observation {obs.observation_id} cutout and preview verified successfully!\n")
    return fits_path, preview_path


def main():
    print("#################################################################")
    print("#  SPHEREx MOVING OBJECT EXPLORER - STEP 2 LIVE VERIFICATION   #")
    print("#################################################################\n")

    # Observation 1: 2025W18_1B_0001_1 (SPHEREx-D4)
    obs1 = SPHERExObservationModel(
        observation_id="2025W18_1B_0001_1",
        ra=276.2413,
        dec=64.8427,
        bandpass="SPHEREx-D4",
        exposure_time_sec=113.58,
        observation_time_utc="2025-04-28 13:00:15.754",
        data_access_url="https://irsa.ipac.caltech.edu/datalink/links/spherex?ID=ivo://irsa.ipac/spherex_qr2_deep?2025W18_1B_0001_1/D4"
    )

    try:
        verify_observation_cutout(obs1, ra=276.26, dec=64.82, size_deg=0.05)
    except Exception as e:
        print(f"[FAILED] Error during observation 1 verification: {e}")
        sys.exit(1)

    print("=" * 65)
    print("Observation 1 succeeded! Now testing second real observation...")
    print("=" * 65 + "\n")

    # Observation 2: 2026W18_1A_0317_1 (SPHEREx-D1)
    obs2 = SPHERExObservationModel(
        observation_id="2026W18_1A_0317_1",
        ra=276.2632,
        dec=64.8225,
        bandpass="SPHEREx-D1",
        exposure_time_sec=113.58,
        observation_time_utc="2026-04-28 12:08:13.949",
        data_access_url="https://irsa.ipac.caltech.edu/datalink/links/spherex?ID=ivo://irsa.ipac/spherex_qr2_deep?2026W18_1A_0317_1/D1"
    )

    try:
        verify_observation_cutout(obs2, ra=276.2632, dec=64.8225, size_deg=0.05)
    except Exception as e:
        print(f"[FAILED] Error during observation 2 verification: {e}")
        sys.exit(1)

    print("#################################################################")
    print("#  ALL STEP 2 LIVE REAL DATA VERIFICATIONS COMPLETED!           #")
    print("#################################################################")


if __name__ == "__main__":
    main()
