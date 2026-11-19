"""
Routeur /geography — Wilayas et Communes d'Algérie.

Les données géographiques sont gérées par l'administrateur via la page Paramètres.
En attendant leur saisie, les listes retournent des tableaux vides avec un message
explicatif — l'application ne se bloque pas.

CRUD complet pour l'ADMIN (ajouter, modifier, supprimer wilayas et communes).
Lecture publique (tout utilisateur authentifié peut lire les listes).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.site import Wilaya, Commune
from app.models.user import User

router = APIRouter(prefix="/geography", tags=["geography"])


# ------------------------------------------------------------------
# Schémas
# ------------------------------------------------------------------
class WilayaOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class WilayaCreate(BaseModel):
    id: int           # code officiel 01-58
    name: str


class WilayaUpdate(BaseModel):
    name: str


class CommuneOut(BaseModel):
    id: int
    wilaya_id: int
    daira: str | None
    name: str

    class Config:
        from_attributes = True


class CommuneCreate(BaseModel):
    wilaya_id: int
    daira: str | None = None
    name: str


class CommuneUpdate(BaseModel):
    daira: str | None = None
    name: str | None = None


# ------------------------------------------------------------------
# WILAYAS — lecture
# ------------------------------------------------------------------
@router.get("/wilayas", response_model=list[WilayaOut])
async def list_wilayas(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WilayaOut]:
    """Retourne toutes les wilayas triées par id. Liste vide si aucune wilaya n'a encore été créée."""
    result = await db.execute(select(Wilaya).order_by(Wilaya.id))
    return result.scalars().all()


@router.get("/wilayas/{wilaya_id}", response_model=WilayaOut)
async def get_wilaya(
    wilaya_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WilayaOut:
    result = await db.execute(select(Wilaya).where(Wilaya.id == wilaya_id))
    wilaya = result.scalar_one_or_none()
    if not wilaya:
        raise HTTPException(status_code=404, detail="Wilaya introuvable")
    return wilaya


# ------------------------------------------------------------------
# WILAYAS — écriture (ADMIN uniquement)
# ------------------------------------------------------------------
@router.post("/wilayas", response_model=WilayaOut, status_code=201)
async def create_wilaya(
    payload: WilayaCreate,
    current_user: User = Depends(require_permission("geography", "write")),
    db: AsyncSession = Depends(get_db),
) -> WilayaOut:
    # Vérifier unicité de l'id
    existing = await db.execute(select(Wilaya).where(Wilaya.id == payload.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"La wilaya {payload.id:02d} existe déjà")
    wilaya = Wilaya(id=payload.id, name=payload.name)
    db.add(wilaya)
    await db.commit()
    await db.refresh(wilaya)
    return wilaya


@router.patch("/wilayas/{wilaya_id}", response_model=WilayaOut)
async def update_wilaya(
    wilaya_id: int,
    payload: WilayaUpdate,
    current_user: User = Depends(require_permission("geography", "write")),
    db: AsyncSession = Depends(get_db),
) -> WilayaOut:
    result = await db.execute(select(Wilaya).where(Wilaya.id == wilaya_id))
    wilaya = result.scalar_one_or_none()
    if not wilaya:
        raise HTTPException(status_code=404, detail="Wilaya introuvable")
    wilaya.name = payload.name
    await db.commit()
    await db.refresh(wilaya)
    return wilaya


@router.delete("/wilayas/{wilaya_id}", status_code=204)
async def delete_wilaya(
    wilaya_id: int,
    current_user: User = Depends(require_permission("geography", "write")),
    db: AsyncSession = Depends(get_db),
) -> None:
    # Vérifier qu'aucune commune n'y est rattachée
    communes_check = await db.execute(
        select(Commune).where(Commune.wilaya_id == wilaya_id).limit(1)
    )
    if communes_check.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Impossible de supprimer : des communes sont rattachées à cette wilaya"
        )
    result = await db.execute(select(Wilaya).where(Wilaya.id == wilaya_id))
    wilaya = result.scalar_one_or_none()
    if not wilaya:
        raise HTTPException(status_code=404, detail="Wilaya introuvable")
    await db.delete(wilaya)
    await db.commit()


# ------------------------------------------------------------------
# COMMUNES — lecture
# ------------------------------------------------------------------
@router.get("/communes", response_model=list[CommuneOut])
async def list_communes(
    wilaya_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CommuneOut]:
    """Retourne les communes, filtrables par wilaya_id. Liste vide si aucune commune n'existe."""
    stmt = select(Commune).order_by(Commune.wilaya_id, Commune.name)
    if wilaya_id is not None:
        stmt = stmt.where(Commune.wilaya_id == wilaya_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/communes/{commune_id}", response_model=CommuneOut)
async def get_commune(
    commune_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommuneOut:
    result = await db.execute(select(Commune).where(Commune.id == commune_id))
    commune = result.scalar_one_or_none()
    if not commune:
        raise HTTPException(status_code=404, detail="Commune introuvable")
    return commune


# ------------------------------------------------------------------
# COMMUNES — écriture (ADMIN uniquement)
# ------------------------------------------------------------------
@router.post("/communes", response_model=CommuneOut, status_code=201)
async def create_commune(
    payload: CommuneCreate,
    current_user: User = Depends(require_permission("geography", "write")),
    db: AsyncSession = Depends(get_db),
) -> CommuneOut:
    # Vérifier que la wilaya existe
    wil = await db.execute(select(Wilaya).where(Wilaya.id == payload.wilaya_id))
    if not wil.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"Wilaya {payload.wilaya_id} introuvable")
    commune = Commune(wilaya_id=payload.wilaya_id, daira=payload.daira, name=payload.name)
    db.add(commune)
    await db.commit()
    await db.refresh(commune)
    return commune


@router.patch("/communes/{commune_id}", response_model=CommuneOut)
async def update_commune(
    commune_id: int,
    payload: CommuneUpdate,
    current_user: User = Depends(require_permission("geography", "write")),
    db: AsyncSession = Depends(get_db),
) -> CommuneOut:
    result = await db.execute(select(Commune).where(Commune.id == commune_id))
    commune = result.scalar_one_or_none()
    if not commune:
        raise HTTPException(status_code=404, detail="Commune introuvable")
    if payload.name is not None:
        commune.name = payload.name
    if payload.daira is not None:
        commune.daira = payload.daira
    await db.commit()
    await db.refresh(commune)
    return commune


@router.delete("/communes/{commune_id}", status_code=204)
async def delete_commune(
    commune_id: int,
    current_user: User = Depends(require_permission("geography", "write")),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Commune).where(Commune.id == commune_id))
    commune = result.scalar_one_or_none()
    if not commune:
        raise HTTPException(status_code=404, detail="Commune introuvable")
    await db.delete(commune)
    await db.commit()
