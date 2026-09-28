import pytest
from typing import List
from unittest.mock import MagicMock, patch

from app.cli_helpers import (
    group_observations_by_date,
    parse_date_indices,
    select_representative_observation,
    validate_dec,
    validate_ra,
    validate_radius,
)
from app.cli import run_cli
from app.models.search import SPHERExObservationModel


# ---------------------------------------------------------------------------
# Test Data Fixtures
# ---------------------------------------------------------------------------

def make_obs(
    obs_id: str,
    date_utc: str,
    ra: float = 276.26,
    dec: float = 64.82,
    url: str = "https://irsa.ipac.caltech.edu/test"
) -> SPHERExObservationModel:
    return SPHERExObservationModel(
        observation_id=obs_id,
        ra=ra,
        dec=dec,
        bandpass="SPHEREx-D1",
        observation_time_mjd=60793.5,
        observation_time_utc=date_utc,
        exposure_time_sec=113.58,
        dataproduct_type="image",
        obs_collection="spherex_qr2_deep",
        data_access_url=url,
        access_format="application/x-votable+xml",
        fov_region="POLYGON ICRS ..."
    )


# ---------------------------------------------------------------------------
# 1. Valid RA/DEC Input
# ---------------------------------------------------------------------------

def test_validate_ra_valid():
    assert validate_ra("0") == 0.0
    assert validate_ra("156.093") == 156.093
    assert validate_ra("360.0") == 360.0
    assert validate_ra("  276.26  ") == 276.26


def test_validate_dec_valid():
    assert validate_dec("-90") == -90.0
    assert validate_dec("-41.645") == -41.645
    assert validate_dec("0.0") == 0.0
    assert validate_dec("90.0") == 90.0
    assert validate_dec("  64.82  ") == 64.82


def test_validate_radius_valid():
    assert validate_radius("") == 30.0
    assert validate_radius("  ") == 30.0
    assert validate_radius("10") == 10.0
    assert validate_radius("120.0") == 120.0


# ---------------------------------------------------------------------------
# 2. Invalid RA
# ---------------------------------------------------------------------------

def test_validate_ra_invalid():
    with pytest.raises(ValueError, match="RA must be between"):
        validate_ra("-0.1")
    with pytest.raises(ValueError, match="RA must be between"):
        validate_ra("360.1")
    with pytest.raises(ValueError, match="RA must be a valid numeric value"):
        validate_ra("invalid_ra")
    with pytest.raises(ValueError, match="RA cannot be empty"):
        validate_ra("")


# ---------------------------------------------------------------------------
# 3. Invalid DEC
# ---------------------------------------------------------------------------

def test_validate_dec_invalid():
    with pytest.raises(ValueError, match="DEC must be between"):
        validate_dec("-90.1")
    with pytest.raises(ValueError, match="DEC must be between"):
        validate_dec("90.1")
    with pytest.raises(ValueError, match="DEC must be a valid numeric value"):
        validate_dec("abc")
    with pytest.raises(ValueError, match="DEC cannot be empty"):
        validate_dec("")


# ---------------------------------------------------------------------------
# 4. Empty Date Selection
# ---------------------------------------------------------------------------

def test_parse_date_indices_empty():
    with pytest.raises(ValueError, match="No dates selected"):
        parse_date_indices("", max_index=5)
    with pytest.raises(ValueError, match="No dates selected"):
        parse_date_indices("   ", max_index=5)
    with pytest.raises(ValueError, match="No dates selected"):
        parse_date_indices(",,,", max_index=5)


# ---------------------------------------------------------------------------
# 5. Invalid Date Index
# ---------------------------------------------------------------------------

def test_parse_date_indices_out_of_range():
    with pytest.raises(ValueError, match="out of range"):
        parse_date_indices("0, 2", max_index=5)
    with pytest.raises(ValueError, match="out of range"):
        parse_date_indices("1, 6", max_index=5)
    with pytest.raises(ValueError, match="Invalid input 'abc'"):
        parse_date_indices("1, abc", max_index=5)


# ---------------------------------------------------------------------------
# 6. Duplicate Date Indices
# ---------------------------------------------------------------------------

def test_parse_date_indices_duplicates_deduplicated():
    # Duplicates are removed, returning unique indices
    assert parse_date_indices("1, 2, 1, 2", max_index=5) == [1, 2]
    assert parse_date_indices("3, 1, 3", max_index=5) == [3, 1]


def test_parse_date_indices_duplicates_reducing_below_minimum():
    # If user provides "2, 2", deduplication leaves only 1 index, which should be rejected
    with pytest.raises(ValueError, match="at least 2 distinct dates"):
        parse_date_indices("2, 2", max_index=5)


# ---------------------------------------------------------------------------
# 7. Selecting At Least Two Valid Dates
# ---------------------------------------------------------------------------

def test_parse_date_indices_minimum_two_dates():
    # Only 1 date selected
    with pytest.raises(ValueError, match="at least 2 distinct dates"):
        parse_date_indices("1", max_index=5)
    # 2 dates selected
    assert parse_date_indices("1, 4", max_index=5) == [1, 4]
    # 3 dates selected
    assert parse_date_indices("1, 3, 5", max_index=5) == [1, 3, 5]


# ---------------------------------------------------------------------------
# 8. Grouping Observations by UTC Calendar Date
# ---------------------------------------------------------------------------

def test_group_observations_by_date():
    obs_list = [
        make_obs("OBS1", "2025-05-05 10:00:00.000"),
        make_obs("OBS2", "2025-04-28 12:00:00.000"),
        make_obs("OBS3", "2025-04-28 14:00:00.000"),
        make_obs("OBS4", "2025-05-12 08:30:00.000"),
    ]
    groups = group_observations_by_date(obs_list)
    
    # Check chronological ordering of keys
    assert list(groups.keys()) == ["2025-04-28", "2025-05-05", "2025-05-12"]
    assert len(groups["2025-04-28"]) == 2
    assert len(groups["2025-05-05"]) == 1
    assert len(groups["2025-05-12"]) == 1
    assert groups["2025-04-28"][0].observation_id == "OBS2"
    assert groups["2025-04-28"][1].observation_id == "OBS3"


# ---------------------------------------------------------------------------
# 9. Deterministic Observation Selection
# ---------------------------------------------------------------------------

def test_select_representative_observation_prefers_valid_url():
    # First obs has no URL, second obs has valid URL -> should select second
    obs_no_url = make_obs("OBS_NO_URL", "2025-04-28 12:00:00", url="")
    obs_with_url = make_obs("OBS_WITH_URL", "2025-04-28 13:00:00", url="https://irsa.ipac.caltech.edu/obs2")
    
    selected = select_representative_observation([obs_no_url, obs_with_url])
    assert selected.observation_id == "OBS_WITH_URL"


def test_select_representative_observation_fallback_to_first():
    # Both have URLs -> selects first
    obs1 = make_obs("OBS_1", "2025-04-28 12:00:00", url="https://irsa.ipac.caltech.edu/obs1")
    obs2 = make_obs("OBS_2", "2025-04-28 13:00:00", url="https://irsa.ipac.caltech.edu/obs2")
    
    selected = select_representative_observation([obs1, obs2])
    assert selected.observation_id == "OBS_1"

    # Neither has URL -> selects first
    obs_no_url1 = make_obs("OBS_NONE_1", "2025-04-28 12:00:00", url="")
    obs_no_url2 = make_obs("OBS_NONE_2", "2025-04-28 13:00:00", url="")
    selected2 = select_representative_observation([obs_no_url1, obs_no_url2])
    assert selected2.observation_id == "OBS_NONE_1"


# ---------------------------------------------------------------------------
# 10. End-to-End CLI Workflow Test (Mocked Service)
# ---------------------------------------------------------------------------

def test_run_cli_mocked():
    mock_observations = [
        make_obs("OBS_DATE1_A", "2025-04-28 12:00:00.000"),
        make_obs("OBS_DATE1_B", "2025-04-28 14:00:00.000"),
        make_obs("OBS_DATE2", "2025-05-05 10:00:00.000"),
        make_obs("OBS_DATE3", "2025-05-12 18:00:00.000"),
    ]
    mock_service = MagicMock(return_value=mock_observations)

    # Simulated user inputs:
    # 1. RA = 276.26
    # 2. DEC = 64.82
    # 3. Radius = [Enter] (default 30)
    # 4. Dates = 1,3
    # 5. Cutout choice = n
    input_queue = ["276.26", "64.82", "", "1,3", "n"]
    printed_lines = []

    def mock_input(prompt: str = "") -> str:
        return input_queue.pop(0)

    def mock_print(*args, **kwargs) -> None:
        printed_lines.append(" ".join(str(a) for a in args))

    result = run_cli(input_func=mock_input, print_func=mock_print, search_service=mock_service)

    # Verify return value
    assert result is not None
    assert len(result) == 2
    date1, obs1, all_obs1 = result[0]
    date2, obs2, all_obs2 = result[1]

    assert date1 == "2025-04-28"
    assert obs1.observation_id == "OBS_DATE1_A"
    assert len(all_obs1) == 2

    assert date2 == "2025-05-12"
    assert obs2.observation_id == "OBS_DATE3"
    assert len(all_obs2) == 1

    # Verify key terminal output strings were printed
    output_text = "\n".join(printed_lines)
    assert "Found 4 real SPHEREx observations." in output_text
    assert "1. 2025-04-28    2 observations" in output_text
    assert "2. 2025-05-05    1 observation" in output_text
    assert "3. 2025-05-12    1 observation" in output_text
    assert "✓ Date 1: real observations found" in output_text
    assert "✓ Date 3: real observations found" in output_text
    assert "SELECTED OBSERVATIONS" in output_text
    assert "Observation ID : OBS_DATE1_A" in output_text
    assert "Observation ID : OBS_DATE3" in output_text


@patch("app.services.fits_service.generate_preview")
@patch("app.services.fits_service.inspect_fits_cutout")
@patch("app.services.cutout_service.fetch_spherex_cutout")
def test_run_cli_with_cutouts_mocked(mock_fetch, mock_inspect, mock_preview, tmp_path):
    mock_observations = [
        make_obs("OBS_CUTOUT_1", "2025-04-28 12:00:00.000"),
        make_obs("OBS_CUTOUT_2", "2025-05-05 10:00:00.000"),
    ]
    mock_service = MagicMock(return_value=mock_observations)

    fake_fits = tmp_path / "mock_cutout.fits"
    fake_fits.touch()
    mock_fetch.return_value = (fake_fits, False)
    mock_inspect.return_value = {
        "science_name": "IMAGE",
        "science_index": 1,
        "image_shape": [29, 29],
        "wcs_available": True,
        "wcs_summary": "RA---TAN/DEC--TAN (~6.15 arcsec/pix)"
    }
    mock_preview.return_value = tmp_path / "mock_preview.png"

    # Inputs: RA, DEC, Radius, Dates, Cutouts (yes), Proceed next (no)
    input_queue = ["276.26", "64.82", "", "1,2", "y", "n"]
    printed_lines = []

    def mock_input(prompt: str = "") -> str:
        return input_queue.pop(0)

    def mock_print(*args, **kwargs) -> None:
        printed_lines.append(" ".join(str(a) for a in args))

    result = run_cli(input_func=mock_input, print_func=mock_print, search_service=mock_service)
    assert result is not None
    output_text = "\n".join(printed_lines)
    assert "✓ Image resource resolved" in output_text
    assert "✓ Valid FITS" in output_text
    assert "✓ WCS available: RA---TAN/DEC--TAN" in output_text
    assert "Preview generated:" in output_text
