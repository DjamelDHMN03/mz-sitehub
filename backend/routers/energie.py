import json
from datetime import date
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from docx import Document

router = APIRouter(prefix="/api/energie", tags=["Energie"])

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = BASE_DIR / "storage" / "templates" / "Demande de Raccordement en Energie Electrique Client FSM BIS.docx"
OUTPUT_DIR = BASE_DIR / "storage" / "demandes_sonelgaz"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = BASE_DIR / "storage" / "sites_energie.json"
PLACEHOLDER_DOTS = "………………………"


class SiteEnergiePayload(BaseModel):
    code_site: str
    nom_site: str
    adresse: str
    longitude: str
    latitude: str
    proprietaire: str
    mode_alimentation: str = "sonelgaz"  # "provisoire" ou "sonelgaz"
    loyer_mensuel_da: int = 18000
    mois_payes: int = 0
    etude_faite: bool = False
    devis_paye: bool = False
    branche: bool = False
    necessite_extension: bool = False
    aps_pret: bool = False
    plan_situation_pret: bool = False
    demande_sonelgaz_prete: bool = False


def _charger_sites() -> list[dict]:
    if not DB_FILE.exists():
        initial = [
            SiteEnergiePayload(
                code_site="AL2238 A",
                nom_site="KOURIFFA",
                adresse="CITE 2400 LOGEMENTS KOURIFFA EL HARRACHE W ALGER",
                longitude="3.141391",
                latitude="36.704134",
                proprietaire="Domaines",
                mode_alimentation="sonelgaz",
                etude_faite=True,
                necessite_extension=True,
                aps_pret=True,
                plan_situation_pret=True,
            ).model_dump()
        ]
        DB_FILE.write_text(json.dumps(initial, indent=2, ensure_ascii=False), encoding="utf-8")
    return json.loads(DB_FILE.read_text(encoding="utf-8"))


def _sauvegarder_sites(sites: list[dict]) -> None:
    DB_FILE.write_text(json.dumps(sites, indent=2, ensure_ascii=False), encoding="utf-8")


@router.get("/sites")
def lister_sites_energie():
    return _charger_sites()


@router.post("/sites")
def enregistrer_site_energie(payload: SiteEnergiePayload):
    sites = _charger_sites()
    updated = False
    for idx, item in enumerate(sites):
        if item["code_site"].strip().lower() == payload.code_site.strip().lower():
            sites[idx] = payload.model_dump()
            updated = True
            break
    if not updated:
        sites.append(payload.model_dump())
    _sauvegarder_sites(sites)
    return payload


@router.post("/sites/{code_site}/generer-demande")
def generer_demande_sonelgaz(code_site: str, date_demande: str = "…………."):
    if not TEMPLATE_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Modele introuvable : {TEMPLATE_PATH}",
        )

    sites = _charger_sites()
    site_item = next(
        (s for s in sites if s["code_site"].strip().lower() == code_site.strip().lower()),
        None,
    )
    if not site_item:
        raise HTTPException(status_code=404, detail="Site introuvable dans le suivi energie.")

    doc = Document(str(TEMPLATE_PATH))
    champs = {
        "Nom du site :": site_item["nom_site"] or PLACEHOLDER_DOTS,
        "Code du site :": site_item["code_site"] or PLACEHOLDER_DOTS,
        "Adresse :": site_item["adresse"] or PLACEHOLDER_DOTS,
        "Longitude :": site_item["longitude"] or PLACEHOLDER_DOTS,
        "Latitude :": site_item["latitude"] or PLACEHOLDER_DOTS,
        "Propriétaire:": site_item["proprietaire"] or PLACEHOLDER_DOTS,
    }

    for p in doc.paragraphs:
        full_text = "".join(r.text for r in p.runs)
        if "Alger," in full_text:
            val_date = date_demande.strip() if date_demande.strip() else "…………."
            for idx, r in enumerate(p.runs):
                if "le" in r.text and idx + 1 < len(p.runs):
                    p.runs[idx + 1].text = f"  {val_date} "
                    for extra in p.runs[idx + 2:]:
                        extra.text = ""
                    break
            continue

        for prefix, val in champs.items():
            if prefix in full_text and len(p.runs) >= 2:
                sep = "  " if prefix == "Propriétaire:" else " "
                suffix = " " if prefix in ("Nom du site :", "Adresse :", "Propriétaire:") else ""
                for idx, r in enumerate(p.runs):
                    if prefix in r.text and idx + 1 < len(p.runs):
                        p.runs[idx + 1].text = f"{sep}{val}{suffix}"
                        for extra in p.runs[idx + 2:]:
                            extra.text = ""
                        break

    safe_code = site_item["code_site"].strip().replace(" ", "_")
    out_path = OUTPUT_DIR / f"Demande_Sonelgaz_{safe_code}_{date.today()}.docx"
    doc.save(str(out_path))

    site_item["demande_sonelgaz_prete"] = True
    _sauvegarder_sites(sites)

    return FileResponse(
        path=str(out_path),
        filename=out_path.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
