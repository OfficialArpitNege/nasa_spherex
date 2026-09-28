"""
Unit tests for Step 3: Motion analysis pipeline.

Tests source detection, WCS conversion, angular separation,
elapsed-time calculation, angular speed, position angle,
cross-matching, classification, and error handling.

All tests use small synthetic arrays; no real NASA data required.
"""
import math
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS

from app.models.motion import (
    AngularDisplacement,
    AngularSpeed,
    CandidateQuality,
    DetectedSource,
    EpochInfo,
    MotionAnalysisRequest,
    MotionAnalysisResult,
    MovingObjectCandidate,
    PixelSkyPosition,
    SourceStatistics,
    TimeDifference,
)
from app.services.cross_matching import (
    compute_angular_separation,
    compute_position_angle,
    cross_match_catalogs,
    position_angle_to_direction,
)
from app.services.motion_analysis import (
    MotionAnalysisError,
    compute_time_difference,
)
from app.services.source_detection import (
    SourceDetectionError,
    detect_sources,
    load_science_image,
    preprocess_image,
)


# ============================================================
# Helper: Create a synthetic FITS file with a simple WCS
# ============================================================

def _make_synthetic_fits(
    tmp_dir: Path,
    filename: str = "test.fits",
    shape: tuple = (29, 29),
    ra_center: float = 276.26,
    dec_center: float = 64.82,
    pixel_scale_deg: float = 6.2 / 3600.0,
    add_sources: bool = True,
    add_variance: bool = True,
    date_obs: str = "2025-04-28T13:00:00",
) -> Path:
    """
    Creates a synthetic SPHEREx-like Multi-Extension FITS file
    with a PRIMARY header, IMAGE HDU, and optional VARIANCE HDU.
    """
    ny, nx = shape

    # Build WCS header
    header = fits.Header()
    header["NAXIS"] = 2
    header["NAXIS1"] = nx
    header["NAXIS2"] = ny
    header["CTYPE1"] = "RA---TAN-SIP"
    header["CTYPE2"] = "DEC--TAN-SIP"
    header["CRPIX1"] = nx / 2.0 + 0.5
    header["CRPIX2"] = ny / 2.0 + 0.5
    header["CRVAL1"] = ra_center
    header["CRVAL2"] = dec_center
    header["CDELT1"] = -pixel_scale_deg  # RA decreases with pixel X
    header["CDELT2"] = pixel_scale_deg
    header["CUNIT1"] = "deg"
    header["CUNIT2"] = "deg"
    header["DATE-OBS"] = date_obs
    header["BANDPASS"] = "SPHEREx-D4"
    header["XPOSURE"] = 113.58

    # Generate image data
    rng = np.random.RandomState(42)
    background = rng.normal(loc=0.5, scale=0.1, size=shape).astype(np.float32)

    if add_sources:
        # Add 3 Gaussian point sources at known positions
        yy, xx = np.mgrid[0:ny, 0:nx]

        # Source 1: center of image
        background += 50.0 * np.exp(-((xx - 14)**2 + (yy - 14)**2) / (2 * 0.8**2))
        # Source 2: offset
        background += 30.0 * np.exp(-((xx - 8)**2 + (yy - 20)**2) / (2 * 0.8**2))
        # Source 3: near edge
        background += 20.0 * np.exp(-((xx - 25)**2 + (yy - 5)**2) / (2 * 0.8**2))

    # Primary HDU (empty, header-only)
    primary = fits.PrimaryHDU()
    primary.header["DATE-OBS"] = date_obs

    # Image HDU
    image_hdu = fits.ImageHDU(data=background, header=header, name="IMAGE")

    hdu_list = [primary, image_hdu]

    # Variance HDU
    if add_variance:
        variance = np.full(shape, 0.01, dtype=np.float32)  # Uniform low variance
        var_header = header.copy()
        var_hdu = fits.ImageHDU(data=variance, header=var_header, name="VARIANCE")
        hdu_list.append(var_hdu)

    hdul = fits.HDUList(hdu_list)
    out_path = tmp_dir / filename
    hdul.writeto(out_path, overwrite=True)

    return out_path


# ============================================================
# Tests: Angular separation
# ============================================================

class TestAngularSeparation:
    def test_zero_separation(self):
        sep = compute_angular_separation(180.0, 45.0, 180.0, 45.0)
        assert sep == pytest.approx(0.0, abs=1e-6)

    def test_known_separation(self):
        # 1 degree apart in DEC at zero RA
        sep = compute_angular_separation(0.0, 0.0, 0.0, 1.0)
        assert sep == pytest.approx(3600.0, abs=0.1)  # 1 deg = 3600 arcsec

    def test_spherical_geometry(self):
        """Verify that separation uses proper spherical distance, not Euclidean."""
        # At DEC=60°, 1 degree of RA corresponds to ~cos(60°)=0.5 degrees on sky
        sep_ra = compute_angular_separation(10.0, 60.0, 11.0, 60.0)
        sep_dec = compute_angular_separation(10.0, 60.0, 10.0, 61.0)
        # RA separation should be roughly half of DEC separation at DEC=60°
        assert sep_ra < sep_dec
        assert sep_ra == pytest.approx(sep_dec * 0.5, rel=0.05)

    def test_antipodal_points(self):
        """Separation between antipodal-like positions should be ~180 degrees."""
        sep = compute_angular_separation(0.0, 0.0, 180.0, 0.0)
        assert sep == pytest.approx(180.0 * 3600.0, abs=1.0)


# ============================================================
# Tests: Position angle
# ============================================================

class TestPositionAngle:
    def test_north(self):
        pa = compute_position_angle(10.0, 50.0, 10.0, 51.0)
        assert pa == pytest.approx(0.0, abs=0.5)

    def test_south(self):
        pa = compute_position_angle(10.0, 51.0, 10.0, 50.0)
        assert pa == pytest.approx(180.0, abs=0.5)

    def test_east(self):
        # East = PA 90° (RA increases to the east in standard coords)
        pa = compute_position_angle(10.0, 0.0, 11.0, 0.0)
        assert pa == pytest.approx(90.0, abs=1.0)

    def test_west(self):
        pa = compute_position_angle(11.0, 0.0, 10.0, 0.0)
        assert pa == pytest.approx(270.0, abs=1.0)


class TestDirectionLabel:
    def test_north(self):
        assert position_angle_to_direction(0.0) == "North"
        assert position_angle_to_direction(359.0) == "North"

    def test_east(self):
        assert position_angle_to_direction(90.0) == "East"

    def test_south(self):
        assert position_angle_to_direction(180.0) == "South"

    def test_west(self):
        assert position_angle_to_direction(270.0) == "West"

    def test_northeast(self):
        assert position_angle_to_direction(45.0) == "Northeast"

    def test_southwest(self):
        assert position_angle_to_direction(225.0) == "Southwest"


# ============================================================
# Tests: Time difference
# ============================================================

class TestTimeDifference:
    def test_utc_strings(self):
        td = compute_time_difference(
            "2025-04-28 13:00:00", "2025-05-28 13:00:00",
            None, None
        )
        assert td.days == pytest.approx(30.0, abs=0.01)
        assert td.hours == pytest.approx(720.0, abs=0.5)
        assert td.seconds == pytest.approx(2592000.0, abs=100.0)

    def test_mjd_fallback(self):
        td = compute_time_difference(
            None, None,
            60793.541667, 60823.541667  # ~30 days apart
        )
        assert td.days == pytest.approx(30.0, abs=0.01)

    def test_missing_timestamps_raises(self):
        with pytest.raises(MotionAnalysisError, match="missing"):
            compute_time_difference(None, None, None, None)

    def test_one_year_apart(self):
        td = compute_time_difference(
            "2025-04-28 13:00:00", "2026-04-28 13:00:00",
            None, None
        )
        assert td.days == pytest.approx(365.0, abs=0.5)


# ============================================================
# Tests: Angular speed
# ============================================================

class TestAngularSpeed:
    def test_simple_speed(self):
        # 10 arcsec displacement over 10 days = 1 arcsec/day
        displacement_arcsec = 10.0
        elapsed_days = 10.0
        speed = displacement_arcsec / elapsed_days
        assert speed == pytest.approx(1.0, abs=1e-6)

    def test_speed_per_hour(self):
        displacement_arcsec = 24.0
        elapsed_days = 1.0
        speed_per_day = displacement_arcsec / elapsed_days
        speed_per_hour = speed_per_day / 24.0
        assert speed_per_hour == pytest.approx(1.0, abs=1e-6)


# ============================================================
# Tests: Image preprocessing
# ============================================================

class TestPreprocessImage:
    def test_normal_image(self):
        data = np.random.normal(loc=1.0, scale=0.1, size=(29, 29))
        cleaned, mean, median, std = preprocess_image(data)
        assert cleaned.shape == (29, 29)
        assert 0.8 < mean < 1.2
        assert std > 0

    def test_nan_replacement(self):
        data = np.ones((10, 10))
        data[5, 5] = np.nan
        data[3, 3] = np.inf
        cleaned, _, _, _ = preprocess_image(data)
        assert np.all(np.isfinite(cleaned))


# ============================================================
# Tests: Source detection with synthetic FITS
# ============================================================

class TestSourceDetection:
    def test_detect_sources_in_synthetic_image(self, tmp_path):
        fits_path = _make_synthetic_fits(tmp_path, add_sources=True)
        data, wcs, meta = load_science_image(fits_path, 276.26, 64.82)
        sources = detect_sources(data, wcs, detection_sigma=3.0, variance=meta.get("variance"))
        # Should detect at least 1 source (the bright center source)
        assert len(sources) >= 1
        # All sources should have valid sky coordinates
        for s in sources:
            assert 0.0 <= s.ra <= 360.0
            assert -90.0 <= s.dec <= 90.0
            assert "valid_wcs" in s.quality_flags

    def test_no_sources_in_uniform_image(self, tmp_path):
        fits_path = _make_synthetic_fits(tmp_path, add_sources=False, filename="uniform.fits")
        data, wcs, meta = load_science_image(fits_path, 276.26, 64.82)
        sources = detect_sources(data, wcs, detection_sigma=10.0)  # Very high threshold
        # Should detect zero or very few noise sources
        assert len(sources) <= 1

    def test_missing_fits_raises(self, tmp_path):
        with pytest.raises(SourceDetectionError, match="not found"):
            load_science_image(Path(tmp_path / "nonexistent.fits"), 0.0, 0.0)

    def test_wcs_metadata_extracted(self, tmp_path):
        fits_path = _make_synthetic_fits(tmp_path)
        _, _, meta = load_science_image(fits_path, 276.26, 64.82)
        assert meta["wcs_projection"] == "RA---TAN-SIP/DEC--TAN-SIP"
        assert meta["bandpass"] == "SPHEREx-D4"

    def test_no_science_hdu_raises(self, tmp_path):
        """FITS file with only a primary HDU (no IMAGE) should raise."""
        primary = fits.PrimaryHDU()
        hdul = fits.HDUList([primary])
        bad_path = tmp_path / "bad.fits"
        hdul.writeto(bad_path)
        with pytest.raises(SourceDetectionError, match="No valid"):
            load_science_image(bad_path, 0.0, 0.0)


# ============================================================
# Tests: Cross-matching
# ============================================================

class TestCrossMatching:
    def _make_source(self, sid, x, y, ra, dec, snr=10.0, flags=None):
        return DetectedSource(
            source_id=sid, x=x, y=y, ra=ra, dec=dec,
            flux=100.0, peak_value=50.0, snr=snr,
            fwhm_pixels=1.5,
            quality_flags=flags or ["valid_wcs", "high_snr"]
        )

    def test_identical_positions_stationary(self):
        s1 = [self._make_source(1, 14.0, 14.0, 276.26, 64.82)]
        s2 = [self._make_source(1, 14.0, 14.0, 276.26, 64.82)]
        candidates, matched, stat, poss, cand, unm = cross_match_catalogs(
            s1, s2, match_tolerance_arcsec=30.0, elapsed_time_days=365.0,
            motion_threshold_arcsec=2.0, candidate_threshold_arcsec=6.2
        )
        assert matched == 1
        assert stat == 1  # Stationary
        assert cand == 0

    def test_large_displacement_candidate(self):
        s1 = [self._make_source(1, 14.0, 14.0, 276.260, 64.820, snr=20.0)]
        # ~10 arcsec displacement in DEC
        s2 = [self._make_source(1, 14.0, 16.0, 276.260, 64.8228, snr=20.0)]
        candidates, matched, stat, poss, cand, unm = cross_match_catalogs(
            s1, s2, match_tolerance_arcsec=30.0, elapsed_time_days=365.0,
            motion_threshold_arcsec=2.0, candidate_threshold_arcsec=6.2
        )
        assert matched == 1
        # Displacement ~10 arcsec > 6.2 threshold, should be candidate
        assert len(candidates) == 1
        assert candidates[0].angular_displacement.arcsec > 6.0
        assert candidates[0].status in ("moving-object-candidate", "possible-motion")

    def test_no_match_beyond_tolerance(self):
        s1 = [self._make_source(1, 14.0, 14.0, 276.26, 64.82)]
        s2 = [self._make_source(1, 14.0, 14.0, 280.0, 60.0)]  # Very far away
        candidates, matched, stat, poss, cand, unm = cross_match_catalogs(
            s1, s2, match_tolerance_arcsec=30.0, elapsed_time_days=365.0
        )
        assert matched == 0
        assert unm == 1

    def test_empty_catalog_1(self):
        s2 = [self._make_source(1, 14.0, 14.0, 276.26, 64.82)]
        candidates, matched, stat, poss, cand, unm = cross_match_catalogs(
            [], s2
        )
        assert matched == 0

    def test_empty_catalog_2(self):
        s1 = [self._make_source(1, 14.0, 14.0, 276.26, 64.82)]
        candidates, matched, stat, poss, cand, unm = cross_match_catalogs(
            s1, []
        )
        assert matched == 0
        assert unm == 1

    def test_position_angle_in_result(self):
        s1 = [self._make_source(1, 14.0, 14.0, 10.0, 50.0, snr=20.0)]
        s2 = [self._make_source(1, 14.0, 16.0, 10.0, 50.003, snr=20.0)]  # ~10.8" north
        candidates, *_ = cross_match_catalogs(
            s1, s2, match_tolerance_arcsec=30.0, elapsed_time_days=365.0,
            motion_threshold_arcsec=2.0, candidate_threshold_arcsec=6.2
        )
        assert len(candidates) == 1
        # Movement is northward → PA should be near 0°
        assert candidates[0].position_angle_deg < 30.0 or candidates[0].position_angle_deg > 330.0
        assert candidates[0].direction_label in ("North", "Northeast", "Northwest")


# ============================================================
# Tests: Different bandpass warning
# ============================================================

class TestBandpassWarning:
    def test_bandpass_mismatch_generates_warning(self, tmp_path):
        # Create two synthetic FITS files
        fits_1 = _make_synthetic_fits(
            tmp_path, "epoch1.fits", date_obs="2025-04-28T13:00:00"
        )
        fits_2 = _make_synthetic_fits(
            tmp_path, "epoch2.fits", date_obs="2025-11-20T13:00:00"
        )

        request = MotionAnalysisRequest(
            fits_path_1=str(fits_1),
            fits_path_2=str(fits_2),
            observation_id_1="obs_A",
            observation_id_2="obs_B",
            ra=276.26,
            dec=64.82,
            timestamp_utc_1="2025-04-28 13:00:00",
            timestamp_utc_2="2025-11-20 13:00:00",
            bandpass_1="SPHEREx-D4",
            bandpass_2="SPHEREx-D1",
        )

        from app.services.motion_analysis import run_motion_analysis
        result = run_motion_analysis(request)
        assert any("BANDPASS MISMATCH" in w for w in result.warnings)

    def test_same_bandpass_no_warning(self, tmp_path):
        fits_1 = _make_synthetic_fits(
            tmp_path, "epoch1.fits", date_obs="2025-04-28T13:00:00"
        )
        fits_2 = _make_synthetic_fits(
            tmp_path, "epoch2.fits", date_obs="2025-11-20T13:00:00"
        )

        request = MotionAnalysisRequest(
            fits_path_1=str(fits_1),
            fits_path_2=str(fits_2),
            observation_id_1="obs_A",
            observation_id_2="obs_B",
            ra=276.26,
            dec=64.82,
            timestamp_utc_1="2025-04-28 13:00:00",
            timestamp_utc_2="2025-11-20 13:00:00",
            bandpass_1="SPHEREx-D4",
            bandpass_2="SPHEREx-D4",
        )

        from app.services.motion_analysis import run_motion_analysis
        result = run_motion_analysis(request)
        assert not any("BANDPASS MISMATCH" in w for w in result.warnings)


# ============================================================
# Tests: Invalid WCS handling
# ============================================================

class TestInvalidWCS:
    def test_no_wcs_keywords_raises(self, tmp_path):
        """FITS with IMAGE HDU but no WCS keywords should raise."""
        header = fits.Header()
        header["NAXIS"] = 2
        header["NAXIS1"] = 10
        header["NAXIS2"] = 10
        data = np.ones((10, 10), dtype=np.float32)

        primary = fits.PrimaryHDU()
        image_hdu = fits.ImageHDU(data=data, header=header, name="IMAGE")
        hdul = fits.HDUList([primary, image_hdu])
        path = tmp_path / "no_wcs.fits"
        hdul.writeto(path)

        with pytest.raises(SourceDetectionError, match="not celestial"):
            load_science_image(path, 0.0, 0.0)


# ============================================================
# Tests: Malformed input
# ============================================================

class TestMalformedInput:
    def test_nonexistent_fits_path(self):
        request = MotionAnalysisRequest(
            fits_path_1="nonexistent_epoch1.fits",
            fits_path_2="nonexistent_epoch2.fits",
            observation_id_1="A", observation_id_2="B",
            ra=0.0, dec=0.0,
            timestamp_utc_1="2025-01-01", timestamp_utc_2="2025-06-01"
        )
        from app.services.motion_analysis import run_motion_analysis
        with pytest.raises(MotionAnalysisError, match="not found"):
            run_motion_analysis(request)


# ============================================================
# Tests: API endpoint
# ============================================================

class TestMotionAPIEndpoint:
    def test_analyze_motion_endpoint_success(self, tmp_path):
        from fastapi.testclient import TestClient
        from app.main import app

        fits_1 = _make_synthetic_fits(
            tmp_path, "epoch1.fits", date_obs="2025-04-28T13:00:00"
        )
        fits_2 = _make_synthetic_fits(
            tmp_path, "epoch2.fits", date_obs="2025-11-20T13:00:00"
        )

        client = TestClient(app)
        response = client.post("/api/analyze-motion", json={
            "fits_path_1": str(fits_1),
            "fits_path_2": str(fits_2),
            "observation_id_1": "test_obs_1",
            "observation_id_2": "test_obs_2",
            "ra": 276.26,
            "dec": 64.82,
            "timestamp_utc_1": "2025-04-28 13:00:00",
            "timestamp_utc_2": "2025-11-20 13:00:00",
        })

        assert response.status_code == 200
        data = response.json()
        assert "analysis_id" in data
        assert "source_statistics" in data
        assert "candidates" in data
        assert "warnings" in data
        assert "scientific_disclaimer" in data

    def test_analyze_motion_missing_fits(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.post("/api/analyze-motion", json={
            "fits_path_1": "nonexistent1.fits",
            "fits_path_2": "nonexistent2.fits",
            "observation_id_1": "A", "observation_id_2": "B",
            "ra": 0.0, "dec": 0.0,
            "timestamp_utc_1": "2025-01-01",
            "timestamp_utc_2": "2025-06-01",
        })
        assert response.status_code == 404

    def test_analyze_motion_missing_timestamps(self, tmp_path):
        from fastapi.testclient import TestClient
        from app.main import app

        fits_1 = _make_synthetic_fits(tmp_path, "epoch1.fits")
        fits_2 = _make_synthetic_fits(tmp_path, "epoch2.fits")

        client = TestClient(app)
        response = client.post("/api/analyze-motion", json={
            "fits_path_1": str(fits_1),
            "fits_path_2": str(fits_2),
            "observation_id_1": "A", "observation_id_2": "B",
            "ra": 276.26, "dec": 64.82,
            # No timestamps
        })
        assert response.status_code == 400


# ============================================================
# Tests: Pydantic model validation
# ============================================================

class TestModelValidation:
    def test_motion_analysis_request_defaults(self):
        req = MotionAnalysisRequest(
            fits_path_1="a.fits", fits_path_2="b.fits",
            observation_id_1="A", observation_id_2="B",
            ra=180.0, dec=0.0,
            timestamp_utc_1="2025-01-01", timestamp_utc_2="2025-06-01"
        )
        assert req.detection_sigma == 3.0
        assert req.match_tolerance_arcsec == 30.0
        assert req.motion_threshold_arcsec == 2.0
        assert req.candidate_threshold_arcsec == 6.2

    def test_detected_source_model(self):
        s = DetectedSource(
            source_id=1, x=14.0, y=14.0, ra=276.26, dec=64.82,
            flux=100.0, peak_value=50.0, snr=15.5, fwhm_pixels=1.5,
            quality_flags=["valid_wcs", "high_snr"]
        )
        assert s.ra == 276.26
        assert "high_snr" in s.quality_flags
