import csv
import io
import logging
from typing import List, Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from astropy.time import Time

from app.config import settings
from app.models.search import SPHERExObservationModel

logger = logging.getLogger(__name__)

class IRSAError(Exception):
    """Base exception for IRSA service errors."""
    pass

class IRSATimeoutError(IRSAError):
    """Raised when request to IRSA times out."""
    pass

class IRSAUpstreamError(IRSAError):
    """Raised when IRSA service returns an HTTP or server error."""
    pass

def validate_search_parameters(
    ra: float,
    dec: float,
    radius_arcmin: float,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Tuple[Optional[float], Optional[float]]:
    """
    Validates RA, DEC, radius, and optional date strings.
    Returns (start_mjd, end_mjd).
    """
    if not (0.0 <= ra <= 360.0):
        raise ValueError(f"RA must be between 0.0 and 360.0 degrees, got {ra}")
    
    if not (-90.0 <= dec <= 90.0):
        raise ValueError(f"DEC must be between -90.0 and 90.0 degrees, got {dec}")
    
    if radius_arcmin <= 0.0 or radius_arcmin > 120.0:
        raise ValueError(f"Search radius must be between 0.0 and 120.0 arcminutes, got {radius_arcmin}")
    
    start_mjd: Optional[float] = None
    if start_date:
        try:
            start_mjd = float(Time(start_date).mjd)
        except (ValueError, TypeError, Exception) as e:
            raise ValueError(f"Invalid start_date format '{start_date}'. Must be ISO date string.") from e
            
    end_mjd: Optional[float] = None
    if end_date:
        try:
            end_mjd = float(Time(end_date).mjd)
        except (ValueError, TypeError, Exception) as e:
            raise ValueError(f"Invalid end_date format '{end_date}'. Must be ISO date string.") from e
            
    if start_mjd is not None and end_mjd is not None and start_mjd > end_mjd:
        raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date})")

    return start_mjd, end_mjd


def parse_csv_response(csv_text: str) -> List[SPHERExObservationModel]:
    """
    Parses CSV output from IRSA TAP spherex.obscore query and normalizes into Pydantic models.
    """
    observations: List[SPHERExObservationModel] = []
    
    if not csv_text or not csv_text.strip():
        return observations
        
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        obs_id = row.get("obs_id")
        if not obs_id:
            continue
            
        try:
            s_ra = float(row.get("s_ra", 0.0))
            s_dec = float(row.get("s_dec", 0.0))
        except (ValueError, TypeError):
            continue
            
        t_min_val = row.get("t_min")
        t_min_mjd: Optional[float] = None
        t_min_iso: Optional[str] = None
        if t_min_val:
            try:
                t_min_mjd = float(t_min_val)
                t_min_iso = Time(t_min_mjd, format="mjd").iso
            except (ValueError, TypeError, Exception):
                t_min_mjd = None
                t_min_iso = None
                
        t_exptime_val = row.get("t_exptime")
        t_exptime: Optional[float] = None
        if t_exptime_val:
            try:
                t_exptime = float(t_exptime_val)
            except (ValueError, TypeError):
                t_exptime = None
                
        obs_model = SPHERExObservationModel(
            observation_id=obs_id,
            ra=s_ra,
            dec=s_dec,
            bandpass=row.get("energy_bandpassname") or None,
            observation_time_mjd=t_min_mjd,
            observation_time_utc=t_min_iso,
            exposure_time_sec=t_exptime,
            dataproduct_type=row.get("dataproduct_type") or None,
            obs_collection=row.get("obs_collection") or None,
            data_access_url=row.get("access_url") or None,
            access_format=row.get("access_format") or None,
            fov_region=row.get("s_region") or None
        )
        observations.append(obs_model)
        
    return observations


def _create_http_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=4,
        connect=3,
        read=3,
        backoff_factor=1.0,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "POST", "HEAD"]),
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def search_spherex_observations(
    ra: float,
    dec: float,
    radius_arcmin: float,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_records: int = 500
) -> List[SPHERExObservationModel]:
    """
    Queries real NASA/IRSA TAP service for SPHEREx observations matching target coordinates and date range.
    """
    start_mjd, end_mjd = validate_search_parameters(ra, dec, radius_arcmin, start_date, end_date)
    radius_deg = radius_arcmin / 60.0
    
    where_clauses = [
        f"1 = CONTAINS(POINT('ICRS', s_ra, s_dec), CIRCLE('ICRS', {ra}, {dec}, {radius_deg}))"
    ]
    if start_mjd is not None:
        where_clauses.append(f"t_min >= {start_mjd}")
    if end_mjd is not None:
        where_clauses.append(f"t_max <= {end_mjd}")
        
    where_str = " AND ".join(where_clauses)
    
    adql_query = f"""
SELECT TOP {max_records}
    obs_id,
    s_ra,
    s_dec,
    energy_bandpassname,
    t_min,
    t_max,
    t_exptime,
    access_url,
    access_format,
    dataproduct_type,
    obs_collection,
    instrument_name,
    s_region
FROM spherex.obscore
WHERE {where_str}
ORDER BY t_min ASC
""".strip()

    logger.info(
        "Executing NASA/IRSA SPHEREx TAP Query: RA=%.4f, DEC=%.4f, Radius=%.2f arcmin, DateRange=[%s, %s]",
        ra, dec, radius_arcmin, start_date or "None", end_date or "None"
    )
    
    params = {
        "REQUEST": "doQuery",
        "LANG": "ADQL",
        "FORMAT": "csv",
        "QUERY": adql_query
    }
    
    headers = {
        "User-Agent": "SPHEREx-Moving-Object-Explorer/0.1.0 (NASA Space Apps 2026)",
        "Accept": "text/csv, application/json, text/plain, */*",
        "Connection": "close"
    }
    
    session = _create_http_session()
    try:
        response = session.post(settings.IRSA_TAP_URL, data=params, headers=headers, timeout=45)
    except requests.exceptions.Timeout as e:
        logger.error("NASA/IRSA service timeout after 45 seconds: %s", e)
        raise IRSATimeoutError("NASA/IRSA service request timed out.") from e
    except requests.exceptions.RequestException as e:
        logger.error("NASA/IRSA service HTTP request failed: %s", e)
        raise IRSAUpstreamError(f"Failed to communicate with NASA/IRSA service: {e}") from e

    logger.info("NASA/IRSA TAP Response HTTP Status: %d", response.status_code)
    
    if response.status_code != 200:
        error_msg = f"NASA/IRSA service returned HTTP {response.status_code}: {response.text[:200]}"
        logger.error(error_msg)
        raise IRSAUpstreamError(error_msg)
        
    observations = parse_csv_response(response.text)
    logger.info("Successfully fetched %d SPHEREx observations from NASA/IRSA", len(observations))
    
    return observations
