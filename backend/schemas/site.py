from pydantic import BaseModel
from typing import Optional

class SiteBase(BaseModel):
    site_id: str
    name: str
    region: str
    latitude: float
    longitude: float
    status: str = "Planned"
    civil_works_progress: float = 0.0

class SiteCreate(SiteBase):
    pass

class SiteResponse(SiteBase):
    id: int

    class Config:
        from_attributes = True
