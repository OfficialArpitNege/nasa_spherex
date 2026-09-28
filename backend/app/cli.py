#!/usr/bin/env python3
"""
Interactive CLI for SPHEREx Moving Object Explorer.
Queries real NASA/IRSA observations, groups them by UTC date,
and allows multi-epoch selection for temporal comparison.
"""

import sys
from typing import Callable, Dict, List, Optional, Tuple

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


def run_cli(
    input_func: Callable[[str], str] = input,
    print_func: Callable[..., None] = print,
    search_service: Callable[..., List[SPHERExObservationModel]] = search_spherex_observations
) -> Optional[List[Tuple[str, SPHERExObservationModel, List[SPHERExObservationModel]]]]:
    """
    Main interactive CLI workflow.
    Returns list of (date_str, selected_obs, all_date_observations) or None if aborted.
    """
    print_func("# SPHEREx Moving Object Explorer\n")

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
            except Exception as e:
                print_func(f"✗ Cutout error: {e}")

            if idx < len(display_items):
                next_choice = input_func("\nProceed to retrieve next observation cutout? [Y/n]: ").strip().lower()
                if next_choice not in ("", "y", "yes"):
                    print_func("Skipping remaining cutouts.")
                    break

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
