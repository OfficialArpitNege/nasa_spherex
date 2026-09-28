import pytest
from typing import List, Optional
from unittest.mock import MagicMock, patch

from app.cli_helpers import (
    group_observations_by_date,
    parse_date_indices,
    select_representative_observation,
    validate_dec,
    validate_ra,
    validate_radius,
)
from app.cli import display_motion_analysis, run_cli
from app.models.motion import (
    AngularDisplacement,
    AngularSpeed,
    CandidateQuality,
    EpochInfo,
    MotionAnalysisResult,
    MovingObjectCandidate,
    PixelSkyPosition,
    SourceStatistics,
    TimeDifference,
)
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


# ---------------------------------------------------------------------------
# 11. Step 3 Motion Analysis CLI Integration Tests
# ---------------------------------------------------------------------------

def make_mock_motion_result(
    candidate_status: str = "stationary",
    trail_path: Optional[str] = None,
    warnings: Optional[List[str]] = None,
) -> MotionAnalysisResult:
    """Creates a structured MotionAnalysisResult fixture for CLI testing."""
    pos1 = PixelSkyPosition(x=14.2, y=15.1, ra=276.251000, dec=64.819000)
    pos2 = PixelSkyPosition(x=14.3, y=15.2, ra=276.252000, dec=64.820000)
    disp = AngularDisplacement(arcsec=1.2345, arcmin=0.020575, degrees=0.000343)
    speed = AngularSpeed(arcsec_per_day=0.1764, arcsec_per_hour=0.00735)
    quality = CandidateQuality(
        snr_epoch_1=10.5,
        snr_epoch_2=11.2,
        centroid_uncertainty_arcsec=0.45,
        cross_match_separation_arcsec=1.2345,
        displacement_to_uncertainty_ratio=2.74,
        confidence="high" if candidate_status == "moving-object-candidate" else "low",
    )
    cand = MovingObjectCandidate(
        candidate_id="candidate_001",
        status=candidate_status,
        evidence=["detected_in_both_epochs", "valid_wcs_epoch_1", "valid_wcs_epoch_2"],
        position_epoch_1=pos1,
        position_epoch_2=pos2,
        angular_displacement=disp,
        average_angular_speed=speed,
        position_angle_deg=45.0,
        direction_label="Northeast",
        quality=quality,
        motion_trail_path=trail_path,
    )
    return MotionAnalysisResult(
        analysis_id="analysis_test123",
        observation_1=EpochInfo(
            observation_id="OBS_CUTOUT_1",
            timestamp_utc="2025-04-28 12:00:00.000",
            ra_center=276.26,
            dec_center=64.82,
            bandpass="SPHEREx-D4",
            fits_path="/fake/path1.fits",
            image_shape=[29, 29],
            wcs_available=True,
            sources_detected=3,
        ),
        observation_2=EpochInfo(
            observation_id="OBS_CUTOUT_2",
            timestamp_utc="2025-05-05 12:00:00.000",
            ra_center=276.26,
            dec_center=64.82,
            bandpass="SPHEREx-D1",
            fits_path="/fake/path2.fits",
            image_shape=[29, 29],
            wcs_available=True,
            sources_detected=3,
        ),
        time_difference=TimeDifference(seconds=604800.0, hours=168.0, days=7.0),
        source_statistics=SourceStatistics(
            sources_detected_epoch_1=3,
            sources_detected_epoch_2=3,
            matched_sources=1,
            stationary_count=1 if candidate_status == "stationary" else 0,
            possible_motion_count=1 if candidate_status == "possible-motion" else 0,
            candidate_count=1 if candidate_status == "moving-object-candidate" else 0,
            unmatched_epoch_1=2,
            unmatched_epoch_2=2,
        ),
        candidates=[cand],
        detection_parameters={"detection_sigma": 3.0},
        warnings=warnings or [],
    )


def test_display_motion_analysis_stationary():
    """Verify CLI display output for stationary sources (no candidates found)."""
    printed_lines = []

    def mock_print(*args, **kwargs) -> None:
        printed_lines.append(" ".join(str(a) for a in args))

    result = make_mock_motion_result(
        candidate_status="stationary",
        warnings=["BANDPASS MISMATCH: Epoch 1 uses SPHEREx-D4, Epoch 2 uses SPHEREx-D1."]
    )

    display_motion_analysis(result, print_func=mock_print)
    output = "\n".join(printed_lines)

    assert "STEP 3: MOTION ANALYSIS" in output
    assert "Observation 1:" in output
    assert "Date: 2025-04-28 12:00:00.000" in output
    assert "Observation ID: OBS_CUTOUT_1" in output
    assert "Bandpass: SPHEREx-D4" in output
    assert "Observation 2:" in output
    assert "Date: 2025-05-05 12:00:00.000" in output
    assert "Observation ID: OBS_CUTOUT_2" in output
    assert "Bandpass: SPHEREx-D1" in output
    assert "Epoch 1 sources: 3" in output
    assert "Epoch 2 sources: 3" in output
    assert "Matched sources: 1" in output
    assert "Moving-object candidates: 0" in output
    assert "## Source / Candidate 001" in output
    assert "Pixel position: (14.20, 15.10)" in output
    assert "RA: 276.251000" in output
    assert "DEC: 64.819000" in output
    assert "Angular displacement:" in output
    assert "1.2345 arcsec" in output
    assert "Elapsed time:" in output
    assert "7.0000 days" in output
    assert "Average angular speed:" in output
    assert "0.1764 arcsec/day" in output
    assert "Position angle:" in output
    assert "45.00 degrees" in output
    assert "Status:\nstationary" in output
    assert "No moving-object candidates were identified in this two-epoch comparison." in output
    assert "This is a valid scientific result." in output
    assert "WARNING:\nBANDPASS MISMATCH: Epoch 1 uses SPHEREx-D4, Epoch 2 uses SPHEREx-D1." in output
    assert "SCIENTIFIC DISCLAIMER:" in output


def test_display_motion_analysis_candidate_with_trail():
    """Verify CLI display output when a moving-object candidate is identified with a motion trail."""
    printed_lines = []

    def mock_print(*args, **kwargs) -> None:
        printed_lines.append(" ".join(str(a) for a in args))

    result = make_mock_motion_result(
        candidate_status="moving-object-candidate",
        trail_path="cache/motion/candidate_001_trail.png",
    )

    display_motion_analysis(result, print_func=mock_print)
    output = "\n".join(printed_lines)

    assert "Moving-object candidates: 1" in output
    assert "## MOVING-OBJECT CANDIDATE" in output
    assert "Candidate ID: candidate_001" in output
    assert "Position at epoch 1:" in output
    assert "Position at epoch 2:" in output
    assert "Angular displacement: 1.2345 arcsec (0.020575 arcmin)" in output
    assert "Elapsed time: 7.0000 days" in output
    assert "Average angular speed: 0.1764 arcsec/day" in output
    assert "Position angle: 45.00 degrees (Northeast)" in output
    assert "Evidence:" in output
    assert "* detected_in_both_epochs" in output
    assert "Motion trail: cache/motion/candidate_001_trail.png" in output


@patch("app.services.fits_service.generate_preview")
@patch("app.services.fits_service.inspect_fits_cutout")
@patch("app.services.cutout_service.fetch_spherex_cutout")
def test_run_cli_with_step3_motion_analysis_mocked(mock_fetch, mock_inspect, mock_preview, tmp_path):
    """Verify end-to-end CLI workflow from search -> date select -> cutout -> Step 3 motion analysis."""
    mock_observations = [
        make_obs("OBS_CUTOUT_1", "2025-04-28 12:00:00.000"),
        make_obs("OBS_CUTOUT_2", "2025-05-05 12:00:00.000"),
    ]
    mock_search = MagicMock(return_value=mock_observations)

    fake_fits1 = tmp_path / "mock_cutout_1.fits"
    fake_fits2 = tmp_path / "mock_cutout_2.fits"
    fake_fits1.touch()
    fake_fits2.touch()
    mock_fetch.side_effect = [(fake_fits1, False), (fake_fits2, False)]
    mock_inspect.return_value = {
        "science_name": "IMAGE",
        "science_index": 1,
        "image_shape": [29, 29],
        "wcs_available": True,
        "wcs_summary": "RA---TAN/DEC--TAN (~6.15 arcsec/pix)"
    }
    mock_preview.return_value = tmp_path / "mock_preview.png"

    mock_motion_result = make_mock_motion_result(candidate_status="stationary")
    mock_motion_service = MagicMock(return_value=mock_motion_result)

    # Inputs: RA, DEC, Radius, Dates (1,2), Cutouts (yes), Proceed next cutout (yes)
    input_queue = ["276.26", "64.82", "", "1,2", "y", "y"]
    printed_lines = []

    def mock_input(prompt: str = "") -> str:
        return input_queue.pop(0)

    def mock_print(*args, **kwargs) -> None:
        printed_lines.append(" ".join(str(a) for a in args))

    result = run_cli(
        input_func=mock_input,
        print_func=mock_print,
        search_service=mock_search,
        motion_service=mock_motion_service,
    )

    assert result is not None
    assert mock_motion_service.called
    call_args = mock_motion_service.call_args[0][0]
    assert call_args.fits_path_1 == str(fake_fits1)
    assert call_args.fits_path_2 == str(fake_fits2)
    assert call_args.observation_id_1 == "OBS_CUTOUT_1"
    assert call_args.observation_id_2 == "OBS_CUTOUT_2"
    assert call_args.ra == 276.26
    assert call_args.dec == 64.82

    output_text = "\n".join(printed_lines)
    assert "STEP 3: MOTION ANALYSIS" in output_text
    assert "Observation 1:" in output_text
    assert "Observation 2:" in output_text
    assert "Source detection:" in output_text
    assert "Epoch 1 sources: 3" in output_text
    assert "Cross matching:" in output_text
    assert "Matched sources: 1" in output_text
    assert "No moving-object candidates were identified in this two-epoch comparison." in output_text


@patch("app.services.fits_service.generate_preview")
@patch("app.services.fits_service.inspect_fits_cutout")
@patch("app.services.cutout_service.fetch_spherex_cutout")
def test_run_cli_with_step3_motion_analysis_error(mock_fetch, mock_inspect, mock_preview, tmp_path):
    """Verify CLI handles Step 3 motion analysis exceptions gracefully."""
    mock_observations = [
        make_obs("OBS_CUTOUT_1", "2025-04-28 12:00:00.000"),
        make_obs("OBS_CUTOUT_2", "2025-05-05 12:00:00.000"),
    ]
    mock_search = MagicMock(return_value=mock_observations)

    fake_fits1 = tmp_path / "mock_cutout_1.fits"
    fake_fits2 = tmp_path / "mock_cutout_2.fits"
    fake_fits1.touch()
    fake_fits2.touch()
    mock_fetch.side_effect = [(fake_fits1, False), (fake_fits2, False)]
    mock_inspect.return_value = {
        "science_name": "IMAGE",
        "science_index": 1,
        "image_shape": [29, 29],
        "wcs_available": True,
        "wcs_summary": "RA---TAN/DEC--TAN"
    }
    mock_preview.return_value = tmp_path / "mock_preview.png"

    mock_motion_service = MagicMock(side_effect=RuntimeError("Cross-matching failed unexpectedly"))

    # Inputs: RA, DEC, Radius, Dates (1,2), Cutouts (yes), Proceed next cutout (yes)
    input_queue = ["276.26", "64.82", "", "1,2", "y", "y"]
    printed_lines = []

    def mock_input(prompt: str = "") -> str:
        return input_queue.pop(0)

    def mock_print(*args, **kwargs) -> None:
        printed_lines.append(" ".join(str(a) for a in args))

    result = run_cli(
        input_func=mock_input,
        print_func=mock_print,
        search_service=mock_search,
        motion_service=mock_motion_service,
    )

    assert result is not None
    output_text = "\n".join(printed_lines)
    assert "✗ Motion analysis error: Cross-matching failed unexpectedly" in output_text

