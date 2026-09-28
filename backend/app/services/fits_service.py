import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from astropy.visualization import PercentileInterval, ZScaleInterval
from astropy.wcs import WCS

logger = logging.getLogger(__name__)


class FITSError(Exception):
    """Base exception for FITS processing errors."""
    pass


class FITSStructureError(FITSError):
    """Raised when FITS file structure is missing expected extensions."""
    pass


class WCSConstructionError(FITSError):
    """Raised when valid WCS cannot be constructed from FITS headers."""
    pass


def inspect_fits_cutout(
    fits_path: Path,
    center_ra: float,
    center_dec: float
) -> Dict[str, Any]:
    """
    Opens a SPHEREx Multi-Extension FITS file, locates the science IMAGE HDU,
    constructs an Astropy WCS, and extracts image geometry and coordinate metadata.
    """
    if not fits_path.exists():
        raise FileNotFoundError(f"FITS file not found at: {fits_path}")

    try:
        hdul = fits.open(fits_path)
    except Exception as e:
        raise FITSError(f"Failed to open FITS file: {e}") from e

    science_hdu = None
    science_index = -1
    science_name = ""

    # Locate the science image HDU
    # 1. Look for extension with name 'IMAGE' and 2D data
    for idx, hdu in enumerate(hdul):
        if hdu.data is not None and getattr(hdu.data, "ndim", 0) == 2:
            if hdu.name.upper() == "IMAGE":
                science_hdu = hdu
                science_index = idx
                science_name = hdu.name
                break

    # 2. Fallback: First 2D HDU with celestial WCS keywords
    if science_hdu is None:
        for idx, hdu in enumerate(hdul):
            if hdu.data is not None and getattr(hdu.data, "ndim", 0) == 2:
                if hdu.header and "CTYPE1" in hdu.header and "CRVAL1" in hdu.header:
                    science_hdu = hdu
                    science_index = idx
                    science_name = hdu.name or f"HDU_{idx}"
                    break

    if science_hdu is None:
        hdul.close()
        raise FITSStructureError(
            f"No valid 2D science IMAGE extension found in FITS MEF {fits_path.name}"
        )

    header = science_hdu.header
    shape = list(science_hdu.data.shape)  # [height, width]

    # Construct WCS
    wcs_obj = None
    wcs_summary = None
    target_pix = None
    try:
        wcs_candidate = WCS(header)
        if wcs_candidate.is_celestial:
            wcs_obj = wcs_candidate
            ctype1 = header.get("CTYPE1", "Unknown")
            ctype2 = header.get("CTYPE2", "Unknown")
            cdelt1 = abs(float(header.get("CDELT1", header.get("CD1_1", 0.0)))) * 3600.0
            wcs_summary = f"{ctype1}/{ctype2} (~{cdelt1:.2f} arcsec/pix)"

            # Compute pixel coordinates of target RA/DEC
            px, py = wcs_obj.world_to_pixel_values(center_ra, center_dec)
            target_pix = [float(px), float(py)]
    except Exception as e:
        logger.warning("Could not construct celestial WCS from header: %s", e)
        wcs_obj = None

    # Primary header metadata fallback
    primary_hdr = hdul[0].header if len(hdul) > 0 else {}
    obs_id = header.get("OBSID", primary_hdr.get("OBSID", header.get("OBS_ID", "Unknown")))
    date_obs = header.get("DATE-OBS", primary_hdr.get("DATE-OBS", None))
    exptime = header.get("XPOSURE", header.get("EXPTIME", primary_hdr.get("EXPTIME", None)))
    bandpass = header.get("BANDPASS", primary_hdr.get("BANDPASS", None))

    data_copy = np.array(science_hdu.data, copy=True)
    hdul.close()

    return {
        "science_index": science_index,
        "science_name": science_name,
        "image_shape": shape,
        "wcs": wcs_obj,
        "wcs_available": wcs_obj is not None,
        "wcs_summary": wcs_summary,
        "target_pixel_coords": target_pix,
        "observation_id": str(obs_id),
        "date_obs": str(date_obs) if date_obs else None,
        "exposure_time": float(exptime) if exptime is not None else None,
        "bandpass": str(bandpass) if bandpass else None,
        "data": data_copy
    }


def generate_preview(
    fits_path: Path,
    output_png_path: Path,
    center_ra: float,
    center_dec: float,
    title: Optional[str] = None
) -> Path:
    """
    Generates an astronomical image preview PNG with percentile-based stretch
    and celestial WCS coordinates.
    """
    output_png_path.parent.mkdir(parents=True, exist_ok=True)

    # Check cache hit for preview
    if output_png_path.exists() and output_png_path.stat().st_size > 1000:
        logger.info("Cache hit for preview PNG: %s", output_png_path)
        return output_png_path

    info = inspect_fits_cutout(fits_path, center_ra=center_ra, center_dec=center_dec)
    data = info["data"]
    wcs = info["wcs"]

    # Filter non-finite pixels for robust stretch
    valid_data = data[np.isfinite(data)]
    if len(valid_data) == 0:
        vmin, vmax = 0.0, 1.0
    else:
        try:
            interval = ZScaleInterval()
            vmin, vmax = interval.get_limits(valid_data)
        except Exception:
            vmin = float(np.percentile(valid_data, 1.0))
            vmax = float(np.percentile(valid_data, 99.0))

    if vmin >= vmax:
        vmax = vmin + 1.0

    # Create figure
    fig = plt.figure(figsize=(7, 7), dpi=150)
    if wcs is not None and wcs.naxis == 2:
        ax = fig.add_subplot(111, projection=wcs)
        try:
            ax.coords.grid(color="white", alpha=0.35, linestyle="--", linewidth=0.7)
            ax.coords["ra"].set_axislabel("Right Ascension (J2000)", fontsize=10)
            ax.coords["dec"].set_axislabel("Declination (J2000)", fontsize=10)
            ax.coords["ra"].set_major_formatter("d.dd")
            ax.coords["dec"].set_major_formatter("d.dd")
        except Exception as e:
            logger.debug("WCSAxes styling note: %s", e)
    else:
        ax = fig.add_subplot(111)
        ax.set_xlabel("Pixel X", fontsize=10)
        ax.set_ylabel("Pixel Y", fontsize=10)

    im = ax.imshow(data, origin="lower", cmap="inferno", vmin=vmin, vmax=vmax)

    # Mark target center coordinate if pixel coords calculated
    if info["target_pixel_coords"] is not None:
        tx, ty = info["target_pixel_coords"]
        ax.plot(tx, ty, marker="+", color="cyan", markersize=14, markeredgewidth=1.5, label="Target Center")
        ax.legend(loc="upper right", fontsize=8, facecolor="black", edgecolor="white", labelcolor="white")

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Surface Brightness (MJy/sr)", fontsize=9)

    display_title = title or f"SPHEREx Cutout: {fits_path.stem}"
    ax.set_title(display_title, fontsize=11, fontweight="bold", pad=12)

    plt.tight_layout()
    fig.savefig(output_png_path, format="png", bbox_inches="tight")
    plt.close(fig)

    logger.info("Generated SPHEREx cutout preview at: %s", output_png_path)
    return output_png_path
