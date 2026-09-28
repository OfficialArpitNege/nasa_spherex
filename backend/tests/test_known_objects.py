"""
Unit tests for the Known Moving Object (3I/ATLAS) service and validation mode.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.models.motion import DetectedSource
from app.services.known_objects import (
    DetectionStatus,
    KnownObjectDetectionResult,
    KnownObjectError,
    KnownObjectObservation,
    TargetAssociationResult,
    associate_target_source,
    evaluate_known_object_detection,
    get_known_object_pair,
    parse_known_object_table,
    to_spherex_observation,
)
from app.services.fits_service import inspect_fits_cutout
from app.cli import display_known_object_analysis, run_cli
from tests.test_cli import make_mock_motion_result


SAMPLE_3I_ATLAS_VOTABLE = """<?xml version="1.0" encoding="utf-8"?>
<VOTABLE version="1.3" xmlns="http://www.ivoa.net/xml/VOTable/v1.3">
  <RESOURCE type="results">
    <TABLE>
      <FIELD name="dataproduct_subtype" datatype="char" arraysize="*" ID="col_0"/>
      <FIELD name="calib_level" datatype="int" ID="col_1"/>
      <FIELD name="obs_id" datatype="char" arraysize="*" ID="col_2"/>
      <FIELD name="obs_title" datatype="char" arraysize="*" ID="col_3"/>
      <FIELD name="spherex_detector" datatype="char" arraysize="*" ID="col_4"/>
      <FIELD name="obs_creator_did" datatype="char" arraysize="*" ID="col_5"/>
      <FIELD name="s_ra" datatype="double" ID="col_6"/>
      <FIELD name="s_dec" datatype="double" ID="col_7"/>
      <FIELD name="comet_ra" datatype="double" ID="col_8"/>
      <FIELD name="comet_dec" datatype="double" ID="col_9"/>
      <FIELD name="t_min" datatype="double" ID="col_10"/>
      <FIELD name="t_max" datatype="double" ID="col_11"/>
      <FIELD name="t_exptime" datatype="float" ID="col_12"/>
      <FIELD name="em_min" datatype="double" ID="col_13"/>
      <FIELD name="em_max" datatype="double" ID="col_14"/>
      <FIELD name="s_region" datatype="char" arraysize="*" ID="col_15"/>
      <FIELD name="dataproduct_type" datatype="char" arraysize="*" ID="col_16"/>
      <FIELD name="access_format" datatype="char" arraysize="*" ID="col_17"/>
      <FIELD name="access_estsize" datatype="float" ID="col_18"/>
      <FIELD name="access_url" datatype="char" arraysize="*" ID="col_19"/>
      <FIELD name="spherex_uuid" datatype="char" arraysize="*" ID="col_20"/>
      <FIELD name="facility_name" datatype="char" arraysize="*" ID="col_21"/>
      <FIELD name="instrument_name" datatype="char" arraysize="*" ID="col_22"/>
      <FIELD name="obs_collection" datatype="char" arraysize="*" ID="col_23"/>
      <FIELD name="target_name" datatype="char" arraysize="*" ID="col_24"/>
      <FIELD name="target_moving" datatype="boolean" ID="col_25"/>
      <DATA>
        <TABLEDATA>
          <TR>
            <TD>spherex.level2</TD>
            <TD>2</TD>
            <TD>2025W32_2D_0017_2</TD>
            <TD>2025W32_2D_0017_2D3 (2025-08-07T14:01)</TD>
            <TD>D3</TD>
            <TD>2025W32_2D_0017_2D3</TD>
            <TD>248.3422936462252</TD>
            <TD>-17.47003484083722</TD>
            <TD>248.3675956158835</TD>
            <TD>-16.999381519011198</TD>
            <TD>60894.58449456</TD>
            <TD>60894.585826939</TD>
            <TD>113.5826</TD>
            <TD>1.6301e-06</TD>
            <TD>2.4346e-06</TD>
            <TD>POLYGON ICRS ...</TD>
            <TD>image</TD>
            <TD>application/x-votable+xml;content=datalink</TD>
            <TD>71634.0</TD>
            <TD>https://irsa.ipac.caltech.edu/datalink/links/spherex?ID=ivo://irsa.ipac/spherex_qr2?2025W32_2D_0017_2/D3</TD>
            <TD>uuid-1</TD>
            <TD>SPHEREx</TD>
            <TD>SPHEREx</TD>
            <TD>spherex_qr2</TD>
            <TD>3I/ATLAS</TD>
            <TD>true</TD>
          </TR>
          <TR>
            <TD>spherex.level2</TD>
            <TD>2</TD>
            <TD>2025W32_2D_0017_4</TD>
            <TD>2025W32_2D_0017_4D3 (2025-08-07T14:05)</TD>
            <TD>D3</TD>
            <TD>2025W32_2D_0017_4D3</TD>
            <TD>248.27722455309151</TD>
            <TD>-17.858127707952864</TD>
            <TD>248.36554451290078</TD>
            <TD>-16.999127816941915</TD>
            <TD>60894.587479074</TD>
            <TD>60894.588811453</TD>
            <TD>113.5826</TD>
            <TD>1.6301e-06</TD>
            <TD>2.4346e-06</TD>
            <TD>POLYGON ICRS ...</TD>
            <TD>image</TD>
            <TD>application/x-votable+xml;content=datalink</TD>
            <TD>71634.0</TD>
            <TD>https://irsa.ipac.caltech.edu/datalink/links/spherex?ID=ivo://irsa.ipac/spherex_qr2?2025W32_2D_0017_4/D3</TD>
            <TD>uuid-2</TD>
            <TD>SPHEREx</TD>
            <TD>SPHEREx</TD>
            <TD>spherex_qr2</TD>
            <TD>3I/ATLAS</TD>
            <TD>true</TD>
          </TR>
        </TABLEDATA>
      </DATA>
    </TABLE>
  </RESOURCE>
</VOTABLE>"""


# ---------------------------------------------------------------------------
# 1. VOTable Parsing & Normalization Tests
# ---------------------------------------------------------------------------

def test_parse_known_object_table(tmp_path):
    votable_file = tmp_path / "test_atlas.vot"
    votable_file.write_text(SAMPLE_3I_ATLAS_VOTABLE, encoding="utf-8")

    obs_list = parse_known_object_table(votable_file)
    assert len(obs_list) == 2

    obs1 = obs_list[0]
    assert obs1.obs_id == "2025W32_2D_0017_2"
    assert obs1.spherex_detector == "D3"
    assert obs1.bandpass == "SPHEREx-D3"
    assert obs1.comet_ra == pytest.approx(248.3675956, abs=1e-6)
    assert obs1.comet_dec == pytest.approx(-16.9993815, abs=1e-6)
    assert "2025-08-07" in obs1.observation_time_utc
    assert "14:01" in obs1.observation_time_utc
    assert obs1.exposure_time_sec == pytest.approx(113.58, abs=0.1)

    obs2 = obs_list[1]
    assert obs2.obs_id == "2025W32_2D_0017_4"
    assert obs2.spherex_detector == "D3"
    assert obs2.comet_ra == pytest.approx(248.3655445, abs=1e-6)
    assert obs2.comet_dec == pytest.approx(-16.9991278, abs=1e-6)
    assert "2025-08-07" in obs2.observation_time_utc
    assert "14:05" in obs2.observation_time_utc


def test_parse_missing_file_raises():
    with pytest.raises(KnownObjectError, match="does not exist"):
        parse_known_object_table(Path("/nonexistent/path/table.vot"))


# ---------------------------------------------------------------------------
# 2. Known Object Pair Selection & Same-Date Support
# ---------------------------------------------------------------------------

def test_get_known_object_pair(tmp_path):
    votable_file = tmp_path / "test_atlas.vot"
    votable_file.write_text(SAMPLE_3I_ATLAS_VOTABLE, encoding="utf-8")

    o1, o2 = get_known_object_pair(votable_path=votable_file)
    assert o1.obs_id == "2025W32_2D_0017_2"
    assert o2.obs_id == "2025W32_2D_0017_4"

    # Both observations are on the SAME calendar date
    assert o1.observation_time_utc[:10] == "2025-08-07"
    assert o2.observation_time_utc[:10] == "2025-08-07"
    assert o1.observation_time_utc != o2.observation_time_utc


def test_get_known_object_pair_missing_raises(tmp_path):
    votable_file = tmp_path / "test_atlas.vot"
    votable_file.write_text(SAMPLE_3I_ATLAS_VOTABLE, encoding="utf-8")

    with pytest.raises(KnownObjectError, match="not found"):
        get_known_object_pair(obs_id_1="NONEXISTENT_OBS", votable_path=votable_file)


# ---------------------------------------------------------------------------
# 3. Observation-Specific Target Coordinates
# ---------------------------------------------------------------------------

def test_to_spherex_observation():
    known_obs = KnownObjectObservation(
        obs_id="2025W32_2D_0017_2",
        observation_time_utc="2025-08-07 14:01:40.330",
        observation_time_mjd=60894.58449456,
        spherex_detector="D3",
        bandpass="SPHEREx-D3",
        comet_ra=248.367595616,
        comet_dec=-16.999381519,
        pointing_ra=248.342294,
        pointing_dec=-17.470035,
        exposure_time_sec=113.58,
        data_access_url="https://irsa.ipac.caltech.edu/test",
    )
    spherex_obs = to_spherex_observation(known_obs)
    assert spherex_obs.observation_id == "2025W32_2D_0017_2"
    assert spherex_obs.bandpass == "SPHEREx-D3"
    assert spherex_obs.data_access_url == "https://irsa.ipac.caltech.edu/test"


# ---------------------------------------------------------------------------
# 4. Predicted vs Measured Comparison Logic (Blind Detection)
# ---------------------------------------------------------------------------

def test_evaluate_known_object_detection_match():
    pred_ra = 248.365545
    pred_dec = -16.999128

    # Source within ~2.8 arcsec
    close_source = DetectedSource(
        source_id=7,
        x=13.81,
        y=13.58,
        ra=248.365240,
        dec=-16.998402,
        flux=0.84,
        snr=11.8,
    )
    distant_source = DetectedSource(
        source_id=1,
        x=20.0,
        y=20.0,
        ra=248.380000,
        dec=-16.980000,
        flux=10.0,
        snr=50.0,
    )

    detected, sep = evaluate_known_object_detection(
        pred_ra, pred_dec, [distant_source, close_source], tolerance_arcsec=15.0
    )
    assert detected is not None
    assert detected.source_id == 7
    assert sep == pytest.approx(2.76, abs=0.2)


def test_evaluate_known_object_detection_no_match():
    pred_ra = 248.367596
    pred_dec = -16.999382

    # Only distant sources
    distant_source = DetectedSource(
        source_id=1,
        x=16.27,
        y=3.87,
        ra=248.374310,
        dec=-16.982600,
        flux=39.8,
        snr=126.6,
    )

    detected, sep = evaluate_known_object_detection(
        pred_ra, pred_dec, [distant_source], tolerance_arcsec=15.0
    )
    # Beyond 15 arcsec tolerance
    assert detected is None
    assert sep is not None
    assert sep > 15.0


def test_evaluate_known_object_detection_empty_catalog():
    detected, sep = evaluate_known_object_detection(248.0, -17.0, [])
    assert detected is None
    assert sep is None


# ---------------------------------------------------------------------------
# 5. Corrected Pixel-Scale Diagnostic Regression Test
# ---------------------------------------------------------------------------

def test_pixel_scale_diagnostic_not_3600(tmp_path):
    from tests.test_cutout import create_test_fits
    fits_file = tmp_path / "scale_test.fits"
    create_test_fits(fits_file, include_wcs=True, include_image=True)

    info = inspect_fits_cutout(fits_file, center_ra=276.26, center_dec=64.82)
    assert info["wcs_available"]
    summary = info["wcs_summary"]
    # Verify diagnostic does not report raw CDELT1 placeholder (3600.00 arcsec/pix)
    assert "3600.00" not in summary
    assert "arcsec/pix" in summary


# ---------------------------------------------------------------------------
# 6. Known Object Mode CLI Report Tests
# ---------------------------------------------------------------------------

def test_display_known_object_analysis_report():
    printed_lines = []

    def mock_print(*args, **kwargs):
        printed_lines.append(" ".join(str(a) for a in args))

    obs1 = KnownObjectObservation(
        obs_id="2025W32_2D_0017_2",
        observation_time_utc="2025-08-07 14:01:40.330",
        observation_time_mjd=60894.58449456,
        spherex_detector="D3",
        bandpass="SPHEREx-D3",
        comet_ra=248.367595616,
        comet_dec=-16.999381519,
        pointing_ra=248.342294,
        pointing_dec=-17.470035,
        exposure_time_sec=113.58,
        data_access_url="https://irsa.ipac.caltech.edu/test1",
    )
    obs2 = KnownObjectObservation(
        obs_id="2025W32_2D_0017_4",
        observation_time_utc="2025-08-07 14:05:58.192",
        observation_time_mjd=60894.587479074,
        spherex_detector="D3",
        bandpass="SPHEREx-D3",
        comet_ra=248.365544513,
        comet_dec=-16.999127817,
        pointing_ra=248.277225,
        pointing_dec=-17.858128,
        exposure_time_sec=113.58,
        data_access_url="https://irsa.ipac.caltech.edu/test2",
    )

    det2 = DetectedSource(
        source_id=7,
        x=13.81,
        y=13.58,
        ra=248.365240,
        dec=-16.998402,
        flux=0.84,
        snr=11.82,
    )

    result = make_mock_motion_result(candidate_status="stationary")

    display_known_object_analysis(
        result=result,
        obs1=obs1,
        obs2=obs2,
        detected_1=None,
        sep_1=31.2,
        detected_2=det2,
        sep_2=2.76,
        val_plot_path=Path("cache/previews/3I_ATLAS_validation.png"),
        print_func=mock_print,
    )

    output = "\n".join(printed_lines)

    assert "KNOWN OBJECT VALIDATION" in output
    assert "Target: 3I/ATLAS" in output
    assert "externally supplied known-object" in output
    assert "Epoch 1" in output
    assert "2025W32_2D_0017_2" in output
    assert "IRSA predicted RA/DEC: 248.367596, -16.999382" in output
    assert "Epoch 2" in output
    assert "2025W32_2D_0017_4" in output
    assert "IRSA predicted RA/DEC: 248.365545, -16.999128" in output
    assert "NO RELIABLE MOVING-OBJECT DETECTION" in output
    assert "PREDICTED VS MEASURED COMPARISON" in output
    assert "Target not reliably detected above threshold" in output
    assert "Separation → 2.76 arcsec" in output
    assert "consistent with supplied ephemeris" in output
    assert "SCIENTIFIC DISCLAIMER:" in output


@patch("app.cli.run_known_object_cli")
def test_run_cli_mode_2_selects_known_object_workflow(mock_known_cli):
    """Verify entering mode '2' in CLI triggers run_known_object_cli."""
    input_queue = ["2"]

    def mock_input(prompt: str = ""):
        return input_queue.pop(0)

    result = run_cli(input_func=mock_input, print_func=lambda *a: None)
    assert mock_known_cli.called
    assert result == []


# ---------------------------------------------------------------------------
# 7. Reusable Target Association Service Regression Tests
# ---------------------------------------------------------------------------

def test_associate_target_source_detected_within_tolerance():
    """Verify target detected within tolerance returns DETECTED with all measured fields."""
    pred_ra = 248.365545
    pred_dec = -16.999128

    source = DetectedSource(
        source_id=7,
        x=13.81,
        y=13.58,
        ra=248.365240,
        dec=-16.998402,
        flux=0.84,
        snr=11.82,
    )

    res = associate_target_source(
        detected_sources=[source],
        predicted_ra=pred_ra,
        predicted_dec=pred_dec,
        max_separation_arcsec=15.0,
        target_name="3I/ATLAS",
        predicted_x=13.50,
        predicted_y=14.00,
    )

    assert isinstance(res, TargetAssociationResult)
    assert res.status == DetectionStatus.DETECTED
    assert res.target_name == "3I/ATLAS"
    assert res.predicted_ra == pred_ra
    assert res.predicted_dec == pred_dec
    assert res.measured_ra == source.ra
    assert res.measured_dec == source.dec
    assert res.measured_x == source.x
    assert res.measured_y == source.y
    assert res.separation_arcsec == pytest.approx(2.82, abs=0.1)
    assert res.pixel_separation is not None
    assert res.pixel_separation == pytest.approx(0.52, abs=0.05)
    assert res.snr == pytest.approx(11.82, abs=0.01)
    assert res.candidate_sources_in_tolerance == 1
    assert res.matched_source == source
    assert "Single source detected" in res.evaluation_note


def test_associate_target_source_outside_tolerance():
    """Verify target outside tolerance returns NOT_DETECTED and does not invent measured coords."""
    pred_ra = 248.367596
    pred_dec = -16.999382

    distant_source = DetectedSource(
        source_id=1,
        x=16.27,
        y=3.87,
        ra=248.374310,
        dec=-16.982600,
        flux=39.8,
        snr=126.6,
    )

    res = associate_target_source(
        detected_sources=[distant_source],
        predicted_ra=pred_ra,
        predicted_dec=pred_dec,
        max_separation_arcsec=15.0,
        target_name="3I/ATLAS",
    )

    assert res.status == DetectionStatus.NOT_DETECTED
    # Scientific rule: do NOT invent a measured position when not detected
    assert res.measured_ra is None
    assert res.measured_dec is None
    assert res.measured_x is None
    assert res.measured_y is None
    assert res.separation_arcsec is None
    assert res.pixel_separation is None
    assert res.snr is None
    assert res.matched_source is None
    assert res.candidate_sources_in_tolerance == 0
    assert res.min_separation_arcsec is not None
    assert res.min_separation_arcsec > 15.0
    assert "Target not detected within" in res.evaluation_note


def test_associate_target_source_no_detected_sources():
    """Verify no detected sources returns NOT_DETECTED cleanly without errors."""
    res = associate_target_source(
        detected_sources=[],
        predicted_ra=248.0,
        predicted_dec=-17.0,
        max_separation_arcsec=15.0,
        target_name="3I/ATLAS",
    )

    assert res.status == DetectionStatus.NOT_DETECTED
    assert res.measured_ra is None
    assert res.measured_dec is None
    assert res.separation_arcsec is None
    assert res.min_separation_arcsec is None
    assert res.candidate_sources_in_tolerance == 0
    assert res.matched_source is None
    assert "no sources detected" in res.evaluation_note.lower()


def test_associate_target_source_ambiguous_multiple_nearby_detections():
    """Verify multiple nearby detections within tolerance returns AMBIGUOUS."""
    pred_ra = 248.365545
    pred_dec = -16.999128

    # Source 1: ~2.5 arcsec away
    s1 = DetectedSource(
        source_id=10,
        x=13.80,
        y=13.60,
        ra=248.365200,
        dec=-16.998450,
        flux=1.2,
        snr=15.0,
    )
    # Source 2: ~4.5 arcsec away (both within 15.0 arcsec)
    s2 = DetectedSource(
        source_id=11,
        x=14.10,
        y=13.90,
        ra=248.365000,
        dec=-16.998000,
        flux=0.9,
        snr=8.5,
    )

    res = associate_target_source(
        detected_sources=[s2, s1],  # passed out of order
        predicted_ra=pred_ra,
        predicted_dec=pred_dec,
        max_separation_arcsec=15.0,
        target_name="3I/ATLAS",
    )

    assert res.status == DetectionStatus.AMBIGUOUS
    assert res.candidate_sources_in_tolerance == 2
    # Nearest valid detected source must still be selected
    assert res.matched_source is not None
    assert res.matched_source.source_id == 10
    assert res.measured_ra == s1.ra
    assert res.measured_dec == s1.dec
    assert res.separation_arcsec == pytest.approx(2.69, abs=0.2)
    assert res.snr == pytest.approx(15.0, abs=0.1)
    assert "Ambiguous association" in res.evaluation_note
    assert "2 detected sources" in res.evaluation_note


def test_one_epoch_detected_one_epoch_not_detected_reports_not_measurable():
    """
    Verify that when one epoch is DETECTED and the other is NOT_DETECTED:
    1. Explicitly reports: 'Two-epoch motion not measurable because the target was not reliably detected in both epochs.'
    2. Does not calculate or display target motion from the two epochs.
    3. Clearly distinguishes predicted vs measured coordinates.
    """
    printed_lines = []

    def mock_print(*args, **kwargs):
        printed_lines.append(" ".join(str(a) for a in args))

    obs1 = KnownObjectObservation(
        obs_id="2025W32_2D_0017_2",
        observation_time_utc="2025-08-07 14:01:40.330",
        observation_time_mjd=60894.58449456,
        spherex_detector="D3",
        bandpass="SPHEREx-D3",
        comet_ra=248.367595616,
        comet_dec=-16.999381519,
        pointing_ra=248.342294,
        pointing_dec=-17.470035,
        exposure_time_sec=113.58,
        data_access_url="https://irsa.ipac.caltech.edu/test1",
    )
    obs2 = KnownObjectObservation(
        obs_id="2025W32_2D_0017_4",
        observation_time_utc="2025-08-07 14:05:58.192",
        observation_time_mjd=60894.587479074,
        spherex_detector="D3",
        bandpass="SPHEREx-D3",
        comet_ra=248.365544513,
        comet_dec=-16.999127817,
        pointing_ra=248.277225,
        pointing_dec=-17.858128,
        exposure_time_sec=113.58,
        data_access_url="https://irsa.ipac.caltech.edu/test2",
    )

    # Epoch 1: NOT_DETECTED
    target_res_1 = TargetAssociationResult(
        target_name="3I/ATLAS",
        predicted_ra=obs1.comet_ra,
        predicted_dec=obs1.comet_dec,
        status=DetectionStatus.NOT_DETECTED,
        measured_ra=None,
        measured_dec=None,
        measured_x=None,
        measured_y=None,
        separation_arcsec=None,
        min_separation_arcsec=31.2,
        evaluation_note="Object emission below stellar point-source detection threshold in this single exposure",
    )

    # Epoch 2: DETECTED
    s2 = DetectedSource(
        source_id=7,
        x=13.81,
        y=13.58,
        ra=248.365240,
        dec=-16.998402,
        flux=0.84,
        snr=11.82,
    )
    target_res_2 = TargetAssociationResult(
        target_name="3I/ATLAS",
        predicted_ra=obs2.comet_ra,
        predicted_dec=obs2.comet_dec,
        status=DetectionStatus.DETECTED,
        measured_ra=s2.ra,
        measured_dec=s2.dec,
        measured_x=s2.x,
        measured_y=s2.y,
        separation_arcsec=2.82,
        pixel_separation=0.46,
        snr=11.82,
        matched_source=s2,
        candidate_sources_in_tolerance=1,
        min_separation_arcsec=2.82,
        evaluation_note="measured position is within the evaluated tolerance of the supplied prediction (consistent with supplied ephemeris)",
    )

    result = make_mock_motion_result(candidate_status="stationary")

    display_known_object_analysis(
        result=result,
        obs1=obs1,
        obs2=obs2,
        print_func=mock_print,
        target_result_1=target_res_1,
        target_result_2=target_res_2,
    )

    output = "\n".join(printed_lines)

    # 1. Must explicitly report exact required message
    assert "Two-epoch motion not measurable because the target was not reliably detected in both epochs." in output

    # 2. Must NOT calculate or display target motion between the two epochs
    assert "## MOVING-OBJECT CANDIDATE" not in output

    # 3. Must clearly distinguish predicted vs measured positions
    assert "Externally supplied predicted position → RA 248.367596, DEC -16.999382" in output
    assert "Independently measured image position  → Target not reliably detected above threshold" in output
    assert "Detection status                       → NOT_DETECTED" in output

    assert "Externally supplied predicted position → RA 248.365545, DEC -16.999128" in output
    assert "Independently measured image position  → RA 248.365240, DEC -16.998402" in output
    assert "Detection status                       → DETECTED" in output
    assert "Separation → 2.82 arcsec" in output


def test_target_association_result_model_contract():
    """Verify TargetAssociationResult model validation, aliases, and serialization."""
    assert KnownObjectDetectionResult is TargetAssociationResult

    res = TargetAssociationResult(
        target_name="3I/ATLAS",
        predicted_ra=248.365545,
        predicted_dec=-16.999128,
        status=DetectionStatus.DETECTED,
        measured_ra=248.365240,
        measured_dec=-16.998402,
        separation_arcsec=2.82,
        evaluation_note="Single source detected within tolerance",
    )

    data = res.model_dump()
    assert data["target_name"] == "3I/ATLAS"
    assert data["status"] == "DETECTED"
    assert data["measured_ra"] == pytest.approx(248.365240)

    # Roundtrip from dict
    restored = TargetAssociationResult.model_validate(data)
    assert restored.status == DetectionStatus.DETECTED
    assert restored.separation_arcsec == 2.82

