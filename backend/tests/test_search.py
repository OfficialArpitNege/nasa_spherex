import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.search import SPHERExObservationModel
from app.services.irsa_service import (
    IRSAUpstreamError,
    parse_csv_response,
    validate_search_parameters,
)

client = TestClient(app)

# ---------------------------------------------------------
# Unit Tests for Parameter Validation
# ---------------------------------------------------------

def test_validate_search_parameters_valid():
    start_mjd, end_mjd = validate_search_parameters(
        ra=156.093,
        dec=-41.645,
        radius_arcmin=10.0,
        start_date="2025-01-01",
        end_date="2026-01-01"
    )
    assert start_mjd is not None
    assert end_mjd is not None
    assert start_mjd < end_mjd

def test_validate_search_parameters_invalid_ra():
    with pytest.raises(ValueError, match="RA must be between"):
        validate_search_parameters(ra=365.0, dec=0.0, radius_arcmin=10.0)

def test_validate_search_parameters_invalid_dec():
    with pytest.raises(ValueError, match="DEC must be between"):
        validate_search_parameters(ra=100.0, dec=-95.0, radius_arcmin=10.0)

def test_validate_search_parameters_invalid_radius():
    with pytest.raises(ValueError, match="Search radius must be between"):
        validate_search_parameters(ra=100.0, dec=0.0, radius_arcmin=0.0)
    with pytest.raises(ValueError, match="Search radius must be between"):
        validate_search_parameters(ra=100.0, dec=0.0, radius_arcmin=150.0)

def test_validate_search_parameters_invalid_date_format():
    with pytest.raises(ValueError, match="Invalid start_date format"):
        validate_search_parameters(ra=100.0, dec=0.0, radius_arcmin=10.0, start_date="invalid-date")

def test_validate_search_parameters_date_order():
    with pytest.raises(ValueError, match="cannot be after end_date"):
        validate_search_parameters(
            ra=100.0, dec=0.0, radius_arcmin=10.0,
            start_date="2026-01-01", end_date="2025-01-01"
        )


# ---------------------------------------------------------
# Unit Tests for Response Normalization
# ---------------------------------------------------------

def test_parse_csv_response():
    mock_csv = """obs_id,s_ra,s_dec,energy_bandpassname,t_min,t_max,t_exptime,access_url,access_format,dataproduct_type,obs_collection,instrument_name,s_region
2025W18_1B_0001_1,276.26393436,64.82395845,SPHEREx-D1,60793.541849,60793.543181,113.582600,https://irsa.ipac.caltech.edu/datalink/links/spherex?ID=ivo://irsa.ipac/spherex_qr2_deep?2025W18_1B_0001_1/D1,application/x-votable+xml;content=datalink,image,spherex_qr2_deep,SPHEREx,POLYGON ICRS 281.9 64.8 276.4 62.3
"""
    observations = parse_csv_response(mock_csv)
    assert len(observations) == 1
    obs = observations[0]
    assert obs.observation_id == "2025W18_1B_0001_1"
    assert obs.ra == pytest.approx(276.26393436)
    assert obs.dec == pytest.approx(64.82395845)
    assert obs.bandpass == "SPHEREx-D1"
    assert obs.observation_time_mjd == pytest.approx(60793.541849)
    assert "2025-04-28" in obs.observation_time_utc
    assert obs.exposure_time_sec == pytest.approx(113.582600)
    assert obs.dataproduct_type == "image"
    assert obs.obs_collection == "spherex_qr2_deep"
    assert "spherex" in obs.data_access_url

def test_parse_csv_response_empty():
    assert parse_csv_response("") == []
    assert parse_csv_response("obs_id,s_ra,s_dec\n") == []


# ---------------------------------------------------------
# API Endpoint Integration Tests (Mocked Service)
# ---------------------------------------------------------

@patch("app.api.search.search_spherex_observations")
def test_search_api_endpoint_success(mock_search):
    mock_search.return_value = [
        SPHERExObservationModel(
            observation_id="TEST_OBS_001",
            ra=156.093,
            dec=-41.645,
            bandpass="SPHEREx-D1",
            observation_time_mjd=60793.5,
            observation_time_utc="2025-05-06 12:00:00.000",
            exposure_time_sec=113.5,
            dataproduct_type="image",
            obs_collection="spherex_qr2_deep",
            data_access_url="https://irsa.ipac.caltech.edu/datalink/links/spherex?ID=test",
            access_format="application/x-votable+xml",
            fov_region="POLYGON ICRS 0 0 1 1"
        )
    ]
    
    response = client.get("/api/search?ra=156.093&dec=-41.645&radius_arcmin=10")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["query"]["ra"] == 156.093
    assert data["observations"][0]["observation_id"] == "TEST_OBS_001"

def test_search_api_endpoint_invalid_ra():
    response = client.get("/api/search?ra=400.0&dec=0.0&radius_arcmin=10")
    assert response.status_code == 422  # FastAPI Pydantic query validation

@patch("app.api.search.search_spherex_observations")
def test_search_api_endpoint_upstream_error(mock_search):
    mock_search.side_effect = IRSAUpstreamError("Connection failed")
    response = client.get("/api/search?ra=156.093&dec=-41.645&radius_arcmin=10")
    assert response.status_code == 502
    assert "NASA/IRSA upstream service error" in response.json()["detail"]
