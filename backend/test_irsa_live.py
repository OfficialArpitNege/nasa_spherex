#!/usr/bin/env python3
"""
Manual live verification script for NASA/IRSA SPHEREx observation search.
Runs a REAL query against NASA/IRSA TAP service.
"""

import sys
import logging
from app.services.irsa_service import search_spherex_observations, IRSAError

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def main():
    print("=" * 60)
    print("  NASA/IRSA SPHEREx LIVE DATA SEARCH VERIFICATION")
    print("=" * 60)
    
    # Test coordinates in SPHEREx sky coverage region
    ra = 276.26
    dec = 64.82
    radius_arcmin = 30.0
    
    print(f"Target Query Parameters:")
    print(f"  RA:            {ra} deg")
    print(f"  DEC:           {dec} deg")
    print(f"  Search Radius: {radius_arcmin} arcmin")
    print("-" * 60)
    
    try:
        observations = search_spherex_observations(
            ra=ra,
            dec=dec,
            radius_arcmin=radius_arcmin,
            max_records=5
        )
    except IRSAError as e:
        print(f"[FAILED] REAL NASA/IRSA Query FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAILED] Unexpected Error: {e}")
        sys.exit(1)

    print(f"[SUCCESS] NASA/IRSA Query Successful!")
    print(f"Total Observations Found: {len(observations)}")
    print("-" * 60)
    
    if not observations:
        print("Zero observations returned for this coordinate and radius.")
    else:
        for idx, obs in enumerate(observations, start=1):
            print(f"Observation #{idx}:")
            print(f"  Observation ID:  {obs.observation_id}")
            print(f"  Collection:      {obs.obs_collection}")
            print(f"  Bandpass:        {obs.bandpass}")
            print(f"  Time (UTC):      {obs.observation_time_utc} (MJD {obs.observation_time_mjd})")
            print(f"  Exposure Time:   {obs.exposure_time_sec} s")
            print(f"  Center (RA,DEC): ({obs.ra:.4f}, {obs.dec:.4f})")
            print(f"  Access URL:      {obs.data_access_url}")
            print(f"  Access Format:   {obs.access_format}")
            print("-" * 60)

if __name__ == "__main__":
    main()
