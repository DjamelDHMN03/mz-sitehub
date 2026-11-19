from fastapi import APIRouter, status, HTTPException
from schemas.site import SiteCreate, SiteResponse
from typing import List

router = APIRouter(prefix="/sites", tags=["GSM Sites"])

# Base de données temporaire en mémoire en attendant le rebranchement de la base
fake_sites_db = []

@router.post("/", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
def create_site(site: SiteCreate):
    for s in fake_sites_db:
        if s["site_id"] == site.site_id:
            raise HTTPException(status_code=400, detail="Ce code de site existe déjà.")
    
    new_site = site.dict()
    new_site["id"] = len(fake_sites_db) + 1
    fake_sites_db.append(new_site)
    return new_site

@router.get("/", response_model=List[SiteResponse])
def get_sites():
    return fake_sites_db
