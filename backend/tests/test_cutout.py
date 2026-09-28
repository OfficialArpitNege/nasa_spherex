import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from astropy.io import fits
from fastapi.testclient import TestClient

from app.main import app
from app.models.search import SPHERExObservationModel
from app.services.cutout_service import (
    CutoutDownloadError,
    DatalinkResolutionError,
    build_cutout_url,
    fetch_spherex_cutout,
    resolve_datalink_fits_url,
    sanitize_identifier,
)
from app.services.fits_service import (
    FITSError,
    FITSStructureError,
    generate_preview,
    inspect_fits_cutout,
)

client = TestClient(app)

SAMPLE_DATALINK_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<VOTABLE version="1.3" xmlns="http://www.ivoa.net/xml/VOTable/v1.3">
  <RESOURCE type="results">
    <TABLE>
      <FIELD name="id" datatype="char" arraysize="*" ID="col_0"/>
      <FIELD name="access_url" datatype="char" arraysize="*" ID="col_1"/>
      <FIELD name="service_def" datatype="char" arraysize="*" ID="col_2"/>
      <FIELD name="error_message" datatype="char" arraysize="*" ID="col_3"/>
      <FIELD name="semantics" datatype="char" arraysize="*" ID="col_4"/>
      <FIELD name="description" datatype="char" arraysize="*" ID="col_5"/>
      <DATA>
        <TABLEDATA>
          <TR>
            <TD>ivo://irsa.ipac/spherex?test</TD>
            <TD>https://irsa.ipac.caltech.edu/ibe/data/spherex/qr2/level2/test_image.fits</TD>
            <TD></TD>
            <TD></TD>
            <TD>#this</TD>
            <TD>Science image</TD>
          </TR>
          <TR>
            <TD>ivo://irsa.ipac/spherex?test</TD>
            <TD></TD>
            <TD>ibe-cutout</TD>
            <TD></TD>
            <TD>#cutout</TD>
            <TD>Cutout service</TD>
          </TR>
        </TABLEDATA>
      </DATA>
    </TABLE>
  </RESOURCE>
</VOTABLE>"""


# Helper to create a valid synthetic FITS file for testing
def create_test_fits(path: Path, include_wcs: bool = True, include_image: bool = True):
    path.parent.mkdir(parents=True, exist_ok=True)
    hdul = fits.HDUList()
    primary = fits.PrimaryHDU()
    hdul.append(primary)

    if include_image:
        data = np.ones((20, 20), dtype=np.float32) * 5.0
        data[10, 10] = 50.0  # Synthetic point source
        img_hdu = fits.ImageHDU(data=data, name="IMAGE")
        if include_wcs:
            img_hdu.header["CTYPE1"] = "RA---TAN"
            img_hdu.header["CTYPE2"] = "DEC--TAN"
            img_hdu.header["CRVAL1"] = 276.26
            img_hdu.header["CRVAL2"] = 64.82
            img_hdu.header["CRPIX1"] = 10.5
            img_hdu.header["CRPIX2"] = 10.5
            img_hdu.header["CDELT1"] = -0.0017
            img_hdu.header["CDELT2"] = 0.0017
        img_hdu.header["OBSID"] = "TEST_OBS_001"
        img_hdu.header["DATE-OBS"] = "2025-04-28T13:00:00"
        img_hdu.header["EXPTIME"] = 113.58
        hdul.append(img_hdu)

    hdul.writeto(path, overwrite=True)


# ---------------------------------------------------------------------------
# 1. Datalink Resolution Tests
# ---------------------------------------------------------------------------

@patch("app.services.cutout_service._create_http_session")
def test_resolve_datalink_fits_url_success(mock_session_factory):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = SAMPLE_DATALINK_XML
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    mock_session_factory.return_value = mock_session

    url = resolve_datalink_fits_url("https://irsa.ipac.caltech.edu/datalink/links/spherex?ID=test")
    assert url == "https://irsa.ipac.caltech.edu/ibe/data/spherex/qr2/level2/test_image.fits"


def test_resolve_datalink_direct_fits_url():
    direct = "https://irsa.ipac.caltech.edu/ibe/data/spherex/qr2/level2/direct.fits"
    assert resolve_datalink_fits_url(direct) == direct


def test_resolve_datalink_untrusted_host():
    with pytest.raises(ValueError, match="Untrusted host"):
        resolve_datalink_fits_url("https://malicious-site.com/datalink")


@patch("app.services.cutout_service._create_http_session")
def test_resolve_datalink_fits_url_not_found(mock_session_factory):
    empty_xml = b"""<?xml version="1.0"?><VOTABLE version="1.3"><RESOURCE><TABLE><DATA><TABLEDATA></TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = empty_xml
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    mock_session_factory.return_value = mock_session

    with pytest.raises(DatalinkResolutionError, match="No usable FITS science image URL"):
        resolve_datalink_fits_url("https://irsa.ipac.caltech.edu/datalink/links/spherex?ID=none")


# ---------------------------------------------------------------------------
# 2. Cutout URL Construction Tests
# ---------------------------------------------------------------------------

def test_build_cutout_url_valid():
    base = "https://irsa.ipac.caltech.edu/ibe/data/spherex/image.fits"
    url = build_cutout_url(base, ra=276.26, dec=64.82, size_deg=0.05)
    assert url == "https://irsa.ipac.caltech.edu/ibe/data/spherex/image.fits?center=276.260000,64.820000&size=0.05"


def test_build_cutout_url_invalid():
    base = "https://irsa.ipac.caltech.edu/ibe/data/spherex/image.fits"
    with pytest.raises(ValueError, match="RA must be between"):
        build_cutout_url(base, ra=-1.0, dec=0.0, size_deg=0.05)
    with pytest.raises(ValueError, match="DEC must be between"):
        build_cutout_url(base, ra=100.0, dec=95.0, size_deg=0.05)
    with pytest.raises(ValueError, match="Cutout size must be between"):
        build_cutout_url(base, ra=100.0, dec=0.0, size_deg=1.5)


def test_sanitize_identifier():
    assert sanitize_identifier("2025W18_1B_0001_1/D4") == "2025W18_1B_0001_1_D4"
    assert sanitize_identifier("../etc/passwd") == ".._etc_passwd"


# ---------------------------------------------------------------------------
# 3. Cutout Retrieval & Download Tests
# ---------------------------------------------------------------------------

@patch("app.services.cutout_service.resolve_datalink_fits_url")
@patch("app.services.cutout_service._create_http_session")
def test_fetch_spherex_cutout_download(mock_session_factory, mock_resolve, tmp_path):
    mock_resolve.return_value = "https://irsa.ipac.caltech.edu/ibe/data/spherex/test.fits"
    
    # Create fake FITS bytes
    fake_fits_bytes = io.BytesIO()
    hdul = fits.HDUList([fits.PrimaryHDU(data=np.zeros((10, 10), dtype=np.float32))])
    hdul.writeto(fake_fits_bytes)
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = fake_fits_bytes.getvalue()
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    mock_session_factory.return_value = mock_session

    obs = SPHERExObservationModel(
        observation_id="TEST_OBS_DOWNLOAD",
        ra=276.26,
        dec=64.82,
        data_access_url="https://irsa.ipac.caltech.edu/datalink/links/spherex?ID=test"
    )

    path, cached = fetch_spherex_cutout(obs, ra=276.26, dec=64.82, size_deg=0.05, cache_dir=tmp_path)
    assert path.exists()
    assert not cached

    # Calling again should result in cache hit
    path2, cached2 = fetch_spherex_cutout(obs, ra=276.26, dec=64.82, size_deg=0.05, cache_dir=tmp_path)
    assert path2 == path
    assert cached2


@patch("app.services.cutout_service.resolve_datalink_fits_url")
@patch("app.services.cutout_service._create_http_session")
def test_fetch_spherex_cutout_invalid_fits_content(mock_session_factory, mock_resolve, tmp_path):
    mock_resolve.return_value = "https://irsa.ipac.caltech.edu/ibe/data/spherex/test.fits"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"<html>Error: Not a FITS file</html>"
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    mock_session_factory.return_value = mock_session

    obs = SPHERExObservationModel(
        observation_id="TEST_INVALID",
        ra=276.26,
        dec=64.82,
        data_access_url="https://irsa.ipac.caltech.edu/datalink"
    )
    with pytest.raises(CutoutDownloadError, match="not a valid FITS file"):
        fetch_spherex_cutout(obs, ra=276.26, dec=64.82, size_deg=0.05, cache_dir=tmp_path)


# ---------------------------------------------------------------------------
# 4. FITS Inspection & WCS Tests
# ---------------------------------------------------------------------------

def test_inspect_fits_cutout_valid(tmp_path):
    fits_file = tmp_path / "valid_test.fits"
    create_test_fits(fits_file, include_wcs=True, include_image=True)

    info = inspect_fits_cutout(fits_file, center_ra=276.26, center_dec=64.82)
    assert info["science_name"] == "IMAGE"
    assert info["science_index"] == 1
    assert info["image_shape"] == [20, 20]
    assert info["wcs_available"]
    assert "RA---TAN" in info["wcs_summary"]
    assert info["target_pixel_coords"] is not None
    # CRPIX was 10.5 (1-based), so 0-based pixel value is ~9.5
    assert info["target_pixel_coords"][0] == pytest.approx(9.5, abs=0.5)


def test_inspect_fits_cutout_missing_wcs(tmp_path):
    fits_file = tmp_path / "no_wcs.fits"
    create_test_fits(fits_file, include_wcs=False, include_image=True)

    info = inspect_fits_cutout(fits_file, center_ra=276.26, center_dec=64.82)
    assert info["science_name"] == "IMAGE"
    assert info["wcs_available"] is False
    assert info["target_pixel_coords"] is None


def test_inspect_fits_cutout_no_image_hdu(tmp_path):
    fits_file = tmp_path / "no_image.fits"
    create_test_fits(fits_file, include_image=False)

    with pytest.raises(FITSStructureError, match="No valid 2D science IMAGE extension"):
        inspect_fits_cutout(fits_file, center_ra=276.26, center_dec=64.82)


# ---------------------------------------------------------------------------
# 5. Preview Generation Tests
# ---------------------------------------------------------------------------

def test_generate_preview(tmp_path):
    fits_file = tmp_path / "preview_test.fits"
    create_test_fits(fits_file, include_wcs=True, include_image=True)

    png_path = tmp_path / "previews" / "preview_test.png"
    result_path = generate_preview(fits_file, png_path, center_ra=276.26, center_dec=64.82)
    assert result_path.exists()
    assert result_path.stat().st_size > 1000


# ---------------------------------------------------------------------------
# 6. POST /api/cutout API Tests
# ---------------------------------------------------------------------------

@patch("app.api.cutout.generate_preview")
@patch("app.api.cutout.inspect_fits_cutout")
@patch("app.api.cutout.fetch_spherex_cutout")
def test_api_cutout_endpoint_success(mock_fetch, mock_inspect, mock_preview, tmp_path):
    fake_fits = tmp_path / "fake.fits"
    fake_fits.touch()

    mock_fetch.return_value = (fake_fits, False)
    mock_inspect.return_value = {
        "science_index": 1,
        "science_name": "IMAGE",
        "image_shape": [29, 29],
        "wcs_available": True,
        "wcs_summary": "RA---TAN/DEC--TAN (~6.15 arcsec/pix)",
        "target_pixel_coords": [14.0, 14.0]
    }
    mock_preview.return_value = tmp_path / "fake_preview.png"

    payload = {
        "observation_id": "2025W18_1B_0001_1",
        "ra": 276.26,
        "dec": 64.82,
        "cutout_size_deg": 0.05,
        "datalink_url": "https://irsa.ipac.caltech.edu/datalink/links/spherex?ID=test",
        "bandpass": "SPHEREx-D4"
    }

    response = client.post("/api/cutout", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["observation_id"] == "2025W18_1B_0001_1"
    assert data["image_shape"] == [29, 29]
    assert data["wcs_available"] is True
    assert data["image_hdu_name"] == "IMAGE"
