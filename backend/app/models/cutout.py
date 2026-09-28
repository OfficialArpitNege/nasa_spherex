from typing import List, Optional
from pydantic import BaseModel, Field


class CutoutRequestModel(BaseModel):
    observation_id: str = Field(..., description="NASA SPHEREx observation ID")
    ra: float = Field(..., ge=0.0, le=360.0, description="Target center Right Ascension in degrees")
    dec: float = Field(..., ge=-90.0, le=90.0, description="Target center Declination in degrees")
    cutout_size_deg: float = Field(0.05, gt=0.0, le=1.0, description="Cutout box size in degrees (default 0.05 deg ~ 3 arcmin)")
    datalink_url: Optional[str] = Field(None, description="Direct NASA/IRSA Datalink access URL")
    bandpass: Optional[str] = Field(None, description="SPHEREx bandpass / detector channel (e.g. SPHEREx-D4)")
    observation_time_utc: Optional[str] = Field(None, description="Observation UTC timestamp")


class CutoutResponseModel(BaseModel):
    status: str = Field(..., description="Operation status ('success')")
    observation_id: str = Field(..., description="NASA SPHEREx observation ID")
    observation_time_utc: Optional[str] = Field(None, description="Observation start time in UTC")
    bandpass: Optional[str] = Field(None, description="SPHEREx bandpass")
    fits_filename: str = Field(..., description="Local FITS cutout filename in cache")
    fits_relative_path: str = Field(..., description="Relative path to local FITS cutout file")
    preview_filename: str = Field(..., description="Preview PNG image filename in cache")
    preview_relative_path: str = Field(..., description="Relative path to preview PNG image")
    image_hdu_index: int = Field(..., description="Index of the science IMAGE HDU in FITS MEF")
    image_hdu_name: str = Field(..., description="Name of the science IMAGE HDU (e.g. 'IMAGE')")
    image_shape: List[int] = Field(..., description="Dimensions of the science image [height, width]")
    wcs_available: bool = Field(..., description="Whether a valid celestial 2D WCS was constructed")
    wcs_summary: Optional[str] = Field(None, description="WCS projection and coordinate description")
    target_pixel_coords: Optional[List[float]] = Field(None, description="Pixel coordinate [x, y] of target RA/DEC")
    center_ra: float = Field(..., description="Requested center RA in degrees")
    center_dec: float = Field(..., description="Requested center DEC in degrees")
    cutout_size_deg: float = Field(..., description="Requested cutout size in degrees")
    cached: bool = Field(..., description="Whether cutout was loaded from existing local cache")
