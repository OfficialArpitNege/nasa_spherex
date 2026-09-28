# SPHEREx Moving Object Explorer

## Project Overview
**SPHEREx Moving Object Explorer** is a public-facing astronomical candidate exploration tool built for NASA Space Apps Challenge 2026. The platform utilizes real NASA/IRSA SPHEREx observations to identify, cross-match, and visualize moving-object candidates across different observation epochs.

## Scientific Purpose & Scientific Principles
- **Scientific Motivation**: The search for hypothetical distant Solar System bodies (such as Planet X / Planet Nine) and unknown Near-Earth Objects (NEOs), Kuiper Belt Objects (KBOs), and asteroids motivates the development of automated moving-object detection pipelines using wide-field astronomical survey data.
- **Strict Scientific Claim Policy**: Planet X serves purely as scientific context and motivation. **Planet X is not detected or identified by this system. The system searches and analyzes SPHEREx observations for moving-object candidates.** All output detections are strictly classified as **"moving-object candidates"** or **"unmatched candidates requiring further scientific investigation."**
- **Data Integrity**: Uses authentic, real NASA/IRSA observations and API services without synthetic or fabricated astronomical data.

---

## NASA/IRSA Data Source & Implementation

### Step 1: Observation Search via TAP
- **Selected Interface**: **IVOA Table Access Protocol (TAP)** via HTTP POST requests using ADQL.
- **Endpoint**: `https://irsa.ipac.caltech.edu/TAP/sync`
- **Target Table**: `spherex.obscore` (IVOA ObsCore standard data model for SPHEREx images and spectra releases).
- **Spatial Query**: ADQL Cone Search `1 = CONTAINS(POINT('ICRS', s_ra, s_dec), CIRCLE('ICRS', {ra}, {dec}, {radius_deg}))`.
- **Temporal Query**: ADQL date bounds `t_min >= {start_mjd}` and `t_max <= {end_mjd}` using Astropy MJD conversion.

### Step 2: Datalink Resolution & SPHEREx Cutout Service
- **Official Documentation Consulted**:
  - [SPHEREx Cutout Tool Documentation](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/cutout_tool.html)
  - [IRSA SPHEREx Data Releases Overview](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_qr.html)
  - [IPAC/Caltech SPHEREx Cutouts Tutorial](https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts/)
- **Datalink Resolution Mechanism**:
  - The TAP query returns an IVOA Datalink URL (`https://irsa.ipac.caltech.edu/datalink/links/spherex?ID=...`).
  - The backend resolves this URL by requesting the IVOA VOTable XML and inspecting rows by semantic role.
  - The row with `semantics="#this"` contains the direct on-premises FITS URL for the level 2 science Multi-Extension FITS (MEF) product (`https://irsa.ipac.caltech.edu/ibe/data/spherex/qr2/...fits`).
- **Cutout Service Query**:
  - As documented by IRSA, cutouts of SPHEREx MEF products are retrieved directly by passing query parameters `?center={ra},{dec}&size={size_deg}` to the resolved on-premises FITS URL.
  - Only the requested spatial subregion is downloaded (~5 MB for a 0.05° cutout vs ~72 MB for the full image).
  - Downloaded FITS files are cached locally under `backend/cache/spherex_<obs_id>_ra<ra>_dec<dec>_size<size>.fits`.
- **FITS Multi-Extension Structure**:
  - HDU 0: `PRIMARY` (PrimaryHDU, header only)
  - HDU 1: `IMAGE` (ImageHDU, float32 science image data with 2D celestial TAN-SIP WCS)
  - HDU 2: `FLAGS` (quality flags)
  - HDU 3: `VARIANCE` (noise/variance map)
  - HDU 4: `ZODI` (zodiacal light model)
  - HDU 5: `PSF` (effective PSF data cube)
  - HDU 6: `WCS-WAVE` (spectral calibration table)
- **WCS & Preview Generation**:
  - Astropy WCS extracts celestial astrometry from the science `IMAGE` HDU header and verifies `wcs.is_celestial`.
  - Matplotlib with Astropy `ZScaleInterval` stretch generates astronomical preview PNGs with `WCSAxes` celestial coordinate grids and target center markers under `backend/cache/previews/`.

---

## API Endpoints

### 1. Health Check
`GET /api/health`
```json
{
  "status": "ok",
  "service": "spherex-moving-object-explorer"
}
```

### 2. Search Real NASA/IRSA SPHEREx Observations
`GET /api/search`

#### Request Parameters:
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `ra` | float | Yes | Right Ascension in degrees (0.0 to 360.0) |
| `dec` | float | Yes | Declination in degrees (-90.0 to 90.0) |
| `radius_arcmin` | float | No (default: 10) | Search radius in arcminutes (0.1 to 120.0) |
| `start_date` | string | No | Optional start date ISO string (e.g. `2025-01-01`) |
| `end_date` | string | No | Optional end date ISO string (e.g. `2026-01-01`) |

#### Example Request:
```http
GET /api/search?ra=276.26&dec=64.82&radius_arcmin=10
```

---

### 3. Retrieve and Inspect SPHEREx FITS Cutout
`POST /api/cutout`

Resolves the observation's Datalink URL, queries the IRSA SPHEREx Cutout Service, caches the FITS cutout locally, inspects HDUs and WCS, and generates a preview PNG.

#### Request Body:
```json
{
  "observation_id": "2025W18_1B_0001_1",
  "data_access_url": "https://irsa.ipac.caltech.edu/datalink/links/spherex?ID=ivo://irsa.ipac/spherex_qr2_deep?2025W18_1B_0001_1/D4",
  "ra": 276.26,
  "dec": 64.82,
  "size_deg": 0.05,
  "observation_time_utc": "2025-04-28 13:00:15.754"
}
```

#### Example Response:
```json
{
  "status": "success",
  "observation_id": "2025W18_1B_0001_1",
  "observation_time_utc": "2025-04-28 13:00:15.754",
  "fits_path": "backend/cache/spherex_2025W18_1B_0001_1_ra276.2600_dec64.8200_size0.0500.fits",
  "preview_path": "backend/cache/previews/spherex_2025W18_1B_0001_1_ra276.2600_dec64.8200_size0.0500_preview.png",
  "image_hdu": "IMAGE",
  "image_shape": [29, 29],
  "wcs_available": true,
  "wcs_summary": "WCS Keywords\nNumber of WCS axes: 2\nCTYPE : 'RA---TAN-SIP'  'DEC--TAN-SIP'  ...",
  "center": {
    "ra": 276.26,
    "dec": 64.82
  },
  "cutout_size_deg": 0.05,
  "cached": true
}
```

---

## Interactive CLI

An interactive terminal interface searches the real SPHEREx archive, inspects temporal coverage, and optionally retrieves and inspects real FITS cutouts for selected observation epochs.

### Command
From the `backend/` directory:
```bash
python -m app.cli
```

### Interactive Workflow
1. **Enter RA / DEC / Radius**: User inputs target sky coordinates (e.g. `RA = 276.26`, `DEC = 64.82`, `Radius = 30 arcmin`).
2. **Real IRSA Search**: Queries real NASA/IRSA SPHEREx observations via the TAP service.
3. **Available Dates Display**: Returned observations are grouped by UTC calendar date and displayed as an indexed list.
4. **User Selects Dates**: User chooses two or more dates to compare (e.g. `1,2`).
5. **Real Observations Displayed**: The CLI outputs observation metadata (Observation IDs, UTC timestamps, pointing coordinates, bandpass, exposure duration, and IRSA access URLs).
6. **Optional Cutout Retrieval**: Prompts user whether to retrieve image cutouts (`[y/N]`). When confirmed:
   - Resolves Datalink VOTables to on-premises FITS URLs.
   - Fetches small spatial cutouts via the SPHEREx Cutout Service.
   - Inspects FITS HDUs and celestial WCS.
   - Generates astronomical preview PNGs with RA/DEC axes.

> [!NOTE]
> **Scientific Disclaimer**: Planet X is NOT detected or identified by this CLI. The tool searches and retrieves authentic NASA SPHEREx observations that will subsequently be analyzed for moving-object candidates.

---

## Quickstart Guide

### 1. Environment & Setup
```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
source venv/bin/activate       # Linux/macOS
pip install -r requirements.txt
```

### 2. Run Pytest Suite
```bash
pytest
```

### 3. Run Interactive CLI
```bash
python -m app.cli
```

### 4. Run Live NASA/IRSA Verification Scripts
```bash
python test_irsa_live.py       # Live TAP search verification
python test_cutout_live.py     # Live Datalink resolution & Cutout verification
```

### 5. Start FastAPI Server
```bash
uvicorn app.main:app --reload
```
- **Interactive API Documentation (Swagger)**: Visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Known Limitations & Scientific Considerations
- **Bandpass Differences**: Observations taken in different detector arrays (e.g., `SPHEREx-D1` vs `SPHEREx-D4`) observe distinct infrared wavelength channels. They cannot be subtracted directly pixel-by-pixel without proper photometric alignment and bandpass consideration (handled in Step 3+).
- **Cutout Size Limits**: The cutout service accepts sizes between `0.01` and `0.5` degrees. Defaults to `0.05` degrees (~29x29 pixels at SPHEREx's 6.2 arcsec/pixel scale).
- **Network Resilience**: IRSA connections use a 30-second timeout with automated retries and explicit `Connection: close` headers to prevent dropped TCP sockets.
