from typing import List, Optional
from pydantic import BaseModel, Field

class SearchQueryModel(BaseModel):
    ra: float = Field(..., ge=0.0, le=360.0, description="Right Ascension in degrees (0..360)")
    dec: float = Field(..., ge=-90.0, le=90.0, description="Declination in degrees (-90..90)")
    radius_arcmin: float = Field(..., gt=0.0, le=120.0, description="Search radius in arcminutes (0..120)")
    start_date: Optional[str] = Field(None, description="Optional start date ISO string (e.g. YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Optional end date ISO string (e.g. YYYY-MM-DD)")

class SPHERExObservationModel(BaseModel):
    observation_id: str = Field(..., description="NASA/IRSA Observation ID")
    ra: float = Field(..., description="Center Right Ascension in degrees")
    dec: float = Field(..., description="Center Declination in degrees")
    bandpass: Optional[str] = Field(None, description="SPHEREx bandpass / spectral channel name")
    observation_time_mjd: Optional[float] = Field(None, description="Observation start time in Modified Julian Date (MJD)")
    observation_time_utc: Optional[str] = Field(None, description="Observation start time converted to ISO UTC string")
    exposure_time_sec: Optional[float] = Field(None, description="Exposure duration in seconds")
    dataproduct_type: Optional[str] = Field(None, description="Data product classification (e.g. image)")
    obs_collection: Optional[str] = Field(None, description="SPHEREx release collection (e.g. spherex_qr2_deep)")
    data_access_url: Optional[str] = Field(None, description="NASA/IRSA Datalink or product access URL")
    access_format: Optional[str] = Field(None, description="Format of data product access link")
    fov_region: Optional[str] = Field(None, description="Spatial sky coverage footprint string")

class SearchResponseModel(BaseModel):
    query: SearchQueryModel
    count: int
    observations: List[SPHERExObservationModel]
