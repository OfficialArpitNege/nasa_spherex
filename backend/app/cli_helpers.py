import re
from typing import Dict, List, Optional
from astropy.time import Time

from app.models.search import SPHERExObservationModel


def validate_ra(ra_input: str) -> float:
    """
    Validates celestial Right Ascension in degrees [0.0, 360.0].
    """
    stripped = str(ra_input).strip()
    if not stripped:
        raise ValueError("RA cannot be empty.")
    try:
        val = float(stripped)
    except (ValueError, TypeError):
        raise ValueError(f"RA must be a valid numeric value, got '{stripped}'")
    
    if not (0.0 <= val <= 360.0):
        raise ValueError(f"RA must be between 0.0 and 360.0 degrees, got {val}")
    return val


def validate_dec(dec_input: str) -> float:
    """
    Validates celestial Declination in degrees [-90.0, 90.0].
    """
    stripped = str(dec_input).strip()
    if not stripped:
        raise ValueError("DEC cannot be empty.")
    try:
        val = float(stripped)
    except (ValueError, TypeError):
        raise ValueError(f"DEC must be a valid numeric value, got '{stripped}'")
    
    if not (-90.0 <= val <= 90.0):
        raise ValueError(f"DEC must be between -90.0 and 90.0 degrees, got {val}")
    return val


def validate_radius(radius_input: str, default: float = 30.0) -> float:
    """
    Validates search radius in arcminutes (0.0, 120.0]. Defaults to 30.0 if empty.
    """
    stripped = str(radius_input).strip()
    if not stripped:
        return default
    try:
        val = float(stripped)
    except (ValueError, TypeError):
        raise ValueError(f"Search radius must be a valid numeric value, got '{stripped}'")
    
    if val <= 0.0 or val > 120.0:
        raise ValueError(f"Search radius must be between 0.0 and 120.0 arcminutes, got {val}")
    return val


def group_observations_by_date(
    observations: List[SPHERExObservationModel]
) -> Dict[str, List[SPHERExObservationModel]]:
    """
    Groups real SPHEREx observations by UTC calendar date (YYYY-MM-DD).
    Returns an OrderedDict/dict sorted chronologically by date.
    """
    groups: Dict[str, List[SPHERExObservationModel]] = {}
    
    for obs in observations:
        date_str: Optional[str] = None
        if obs.observation_time_utc:
            # Extract YYYY-MM-DD from 'YYYY-MM-DD HH:MM:SS.sss' or ISO string
            match = re.match(r"^(\d{4}-\d{2}-\d{2})", obs.observation_time_utc.strip())
            if match:
                date_str = match.group(1)
        
        if not date_str and obs.observation_time_mjd is not None:
            try:
                date_str = Time(obs.observation_time_mjd, format="mjd").iso[:10]
            except Exception:
                date_str = None
                
        if not date_str:
            date_str = "Unknown"
            
        if date_str not in groups:
            groups[date_str] = []
        groups[date_str].append(obs)
        
    # Sort dates chronologically; place Unknown at the end if present
    known_dates = sorted([d for d in groups.keys() if d != "Unknown"])
    sorted_groups: Dict[str, List[SPHERExObservationModel]] = {
        d: groups[d] for d in known_dates
    }
    if "Unknown" in groups:
        sorted_groups["Unknown"] = groups["Unknown"]
        
    return sorted_groups


def parse_date_indices(selection_str: str, max_index: int) -> List[int]:
    """
    Parses and validates comma-separated date indices from user input (1-based indexing).
    - Removes duplicate indices while preserving initial order.
    - Requires at least 2 distinct valid indices for temporal comparison.
    - Rejects invalid formats and out-of-range indices.
    """
    stripped = selection_str.strip()
    if not stripped:
        raise ValueError("No dates selected. Please enter at least two comma-separated date numbers.")
    
    parts = [p.strip() for p in stripped.split(",") if p.strip()]
    if not parts:
        raise ValueError("No dates selected. Please enter at least two comma-separated date numbers.")
        
    indices: List[int] = []
    for part in parts:
        try:
            idx = int(part)
        except ValueError:
            raise ValueError(f"Invalid input '{part}'. Expected comma-separated numbers.")
            
        if idx < 1 or idx > max_index:
            raise ValueError(
                f"Selected index {idx} is out of range. Valid range: 1 to {max_index}."
            )
        indices.append(idx)
        
    # Remove duplicates while preserving original order
    unique_indices = list(dict.fromkeys(indices))
    
    if len(unique_indices) < 2:
        raise ValueError(
            f"Please select at least 2 distinct dates for comparison (got {len(unique_indices)})."
        )
        
    return unique_indices


def select_representative_observation(
    observations: List[SPHERExObservationModel]
) -> SPHERExObservationModel:
    """
    Deterministically selects one representative observation from a list of observations on the same date.
    Deterministic Rule:
      1. Prefers an observation with a non-empty data_access_url.
      2. If multiple or none have a URL, selects the first observation in chronological order.
    
    Note: All observations for the date remain available in the group for subsequent multi-observation processing.
    """
    if not observations:
        raise ValueError("Cannot select from an empty observation list.")
        
    with_url = [obs for obs in observations if obs.data_access_url and obs.data_access_url.strip()]
    if with_url:
        return with_url[0]
    return observations[0]
