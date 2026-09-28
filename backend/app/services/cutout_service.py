import io
import logging
import os
import re
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import requests
from astropy.io.votable import parse_single_table

from app.config import settings
from app.models.search import SPHERExObservationModel
from app.services.irsa_service import _create_http_session

logger = logging.getLogger(__name__)

# Allowed NASA/IRSA hosts for security validation
ALLOWED_IRSA_HOSTS = {"irsa.ipac.caltech.edu", "irsatest.ipac.caltech.edu"}


class CutoutError(Exception):
    """Base exception for SPHEREx cutout errors."""
    pass


class DatalinkResolutionError(CutoutError):
    """Raised when an IVOA Datalink URL cannot be resolved to a FITS resource."""
    pass


class CutoutDownloadError(CutoutError):
    """Raised when downloading a SPHEREx cutout fails."""
    pass


def sanitize_identifier(identifier: str) -> str:
    """
    Sanitizes an observation identifier for safe filesystem usage.
    """
    cleaned = re.sub(r"[^A-Za-z0-9_\-\.]", "_", identifier.strip())
    return cleaned[:100]


def validate_irsa_url(url: str) -> None:
    """
    Ensures that a URL targets an approved NASA/IRSA host to prevent SSRF vulnerabilities.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme: '{parsed.scheme}'. Must be http or https.")
    if parsed.hostname not in ALLOWED_IRSA_HOSTS:
        raise ValueError(f"Untrusted host '{parsed.hostname}'. Only NASA/IRSA endpoints are permitted.")


def resolve_datalink_fits_url(datalink_url: str) -> str:
    """
    Resolves an official IVOA Datalink URL into a direct on-premises SPHEREx FITS image URL.
    Inspects the Datalink VOTable output for the primary science image (semantics='#this').
    """
    validate_irsa_url(datalink_url)

    # If the URL is already an on-premises FITS URL, return it directly
    if datalink_url.endswith(".fits") and "/ibe/data/" in datalink_url:
        return datalink_url.split("?")[0]

    logger.info("Resolving NASA/IRSA Datalink resource: %s", datalink_url)
    session = _create_http_session()

    headers = {
        "User-Agent": "SPHEREx-Moving-Object-Explorer/0.1.0 (NASA Space Apps 2026)",
        "Accept": "application/x-votable+xml, text/xml, */*",
        "Connection": "close"
    }

    try:
        response = session.get(datalink_url, headers=headers, timeout=30)
    except requests.exceptions.RequestException as e:
        logger.error("Failed to query Datalink service: %s", e)
        raise DatalinkResolutionError(f"Network error querying Datalink endpoint: {e}") from e

    if response.status_code != 200:
        raise DatalinkResolutionError(
            f"Datalink endpoint returned HTTP {response.status_code}: {response.text[:200]}"
        )

    try:
        table = parse_single_table(io.BytesIO(response.content)).to_table()
    except Exception as e:
        logger.error("Failed to parse Datalink VOTable XML: %s", e)
        raise DatalinkResolutionError(f"Could not parse Datalink VOTable: {e}") from e

    # In IRSA Datalink VOTable:
    # col_1: access_url
    # col_4: semantics (e.g. '#this', '#cutout', '#calibration')
    # col_6: format (e.g. 'image/fits')
    # We look for the main science image: semantics '#this' and access_url ending in .fits
    fits_url: Optional[str] = None

    # First pass: Look for semantics == '#this' with .fits
    for row in table:
        row_dict = {col: str(row[col]).strip() for col in table.colnames}
        semantics = row_dict.get("col_4", "")
        access_url = row_dict.get("col_1", "")
        if semantics == "#this" and access_url.endswith(".fits"):
            fits_url = access_url
            break

    # Second pass fallback: Any row with access_url ending in .fits and not '#calibration'
    if not fits_url:
        for row in table:
            row_dict = {col: str(row[col]).strip() for col in table.colnames}
            access_url = row_dict.get("col_1", "")
            semantics = row_dict.get("col_4", "")
            if access_url.endswith(".fits") and semantics != "#calibration":
                fits_url = access_url
                break

    if not fits_url:
        raise DatalinkResolutionError(
            f"No usable FITS science image URL discovered in Datalink response for {datalink_url}"
        )

    validate_irsa_url(fits_url)
    logger.info("Successfully resolved Datalink to FITS image URL: %s", fits_url)
    return fits_url


def build_cutout_url(fits_url: str, ra: float, dec: float, size_deg: float = 0.05) -> str:
    """
    Constructs the official IRSA SPHEREx Cutout Service URL by appending
    center coordinates and box size parameters.
    Example:
      https://irsa.ipac.caltech.edu/ibe/data/...fits?center=276.26,64.82&size=0.05
    """
    if not (0.0 <= ra <= 360.0):
        raise ValueError(f"RA must be between 0.0 and 360.0, got {ra}")
    if not (-90.0 <= dec <= 90.0):
        raise ValueError(f"DEC must be between -90.0 and 90.0, got {dec}")
    if size_deg <= 0.0 or size_deg > 1.0:
        raise ValueError(f"Cutout size must be between 0.001 and 1.0 degrees, got {size_deg}")

    base_url = fits_url.split("?")[0]
    return f"{base_url}?center={ra:.6f},{dec:.6f}&size={size_deg}"


def fetch_spherex_cutout(
    observation: SPHERExObservationModel,
    ra: float,
    dec: float,
    size_deg: float = 0.05,
    cache_dir: Optional[Path] = None
) -> Tuple[Path, bool]:
    """
    Retrieves a small SPHEREx FITS cutout from the official IRSA Cutout Service.
    Checks the local cache directory first. If already downloaded and valid, returns the cached file.
    Otherwise, resolves the Datalink URL, queries the Cutout Service, saves to cache, and returns (Path, cached).
    """
    if cache_dir is None:
        cache_dir = Path(settings.CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)

    safe_id = sanitize_identifier(observation.observation_id)
    band_id = sanitize_identifier(observation.bandpass or "band")
    filename = f"spherex_{safe_id}_{band_id}_{ra:.4f}_{dec:.4f}_{size_deg}deg.fits"
    local_path = cache_dir / filename

    # Check cache hit
    if local_path.exists() and local_path.stat().st_size > 2880:
        try:
            with open(local_path, "rb") as f:
                header_bytes = f.read(80)
                if header_bytes.startswith(b"SIMPLE  ="):
                    logger.info("Cache hit for SPHEREx cutout: %s", local_path)
                    return local_path, True
        except Exception as e:
            logger.warning("Existing cached cutout %s was invalid, re-downloading: %s", local_path, e)

    if not observation.data_access_url:
        raise CutoutError(
            f"Observation '{observation.observation_id}' does not have a data_access_url."
        )

    # 1. Resolve Datalink into direct FITS URL
    fits_url = resolve_datalink_fits_url(observation.data_access_url)

    # 2. Build cutout URL
    cutout_url = build_cutout_url(fits_url, ra=ra, dec=dec, size_deg=size_deg)
    logger.info("Requesting SPHEREx Cutout: %s", cutout_url)

    # 3. Download cutout
    session = _create_http_session()
    headers = {
        "User-Agent": "SPHEREx-Moving-Object-Explorer/0.1.0 (NASA Space Apps 2026)",
        "Accept": "application/fits, image/fits, */*",
        "Connection": "close"
    }

    try:
        response = session.get(cutout_url, headers=headers, timeout=60, stream=True)
    except requests.exceptions.RequestException as e:
        logger.error("Cutout download failed for %s: %s", cutout_url, e)
        raise CutoutDownloadError(f"Network error downloading cutout: {e}") from e

    if response.status_code != 200:
        raise CutoutDownloadError(
            f"Cutout service returned HTTP {response.status_code}: {response.text[:200]}"
        )

    # Read content and verify standard FITS header
    content = response.content
    if not content.startswith(b"SIMPLE  ="):
        error_preview = content[:200].decode("utf-8", errors="replace")
        raise CutoutDownloadError(
            f"Response is not a valid FITS file. Received: {error_preview}"
        )

    # Write atomically via temp file
    temp_path = local_path.with_suffix(".tmp")
    with open(temp_path, "wb") as f:
        f.write(content)
    temp_path.replace(local_path)

    logger.info("Successfully downloaded and cached SPHEREx cutout to: %s (%d bytes)", local_path, len(content))
    return local_path, False
