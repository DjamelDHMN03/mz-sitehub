from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
import models

router = APIRouter(prefix="/geospatial", tags=["Geospatial"])

@router.post("/upload-kmz-report")
async def upload_kmz_report(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename.endswith((".kmz", ".kml")):
        raise HTTPException(status_code=400, detail="Le fichier doit être au format KMZ ou KML.")
    
    # 1. Votre logique actuelle de parsing (zipfile + BeautifulSoup / extraction des coordonnées)
    # Exemple de données simulées ou extraites de votre parseur :
    parsed_sites = [] # Remplacez par le résultat de votre fonction de parsing KMZ existante

    # 2. Enregistrement en base de données Supabase
    saved_count = 0
    for site in parsed_sites:
        db_site = models.TelecomSiteModel(
            site_id=site["site_id"],
            site_name=site["site_name"],
            latitude=site["latitude"],
            longitude=site["longitude"],
            wilaya=site.get("wilaya"),
            source_kmz=file.filename
        )
        db.add(db_site)
        saved_count += 1

    return {
        "status": "success",
        "filename": file.filename,
        "sites_saved": saved_count,
        "message": f"Fichier analysé et {saved_count} sites enregistrés avec succès dans Supabase !"
    }
