"""
Routeur /sites — CRUD complet, flexibilité totale des champs (section 16),
gestion du changement de code avec confirmation (section 17), soft delete +
corbeille (section 18), audit (section 19), recherche/filtres (section 58).
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.shape import to_shape
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.audit import log_audit
from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.site import Site
from app.models.user import User
from app.schemas.site import (
    CodeChangeConfirm,
    SiteCreate,
    SiteListItem,
    SiteListResponse,
    SiteOut,
    SiteUpdate,
)

router = APIRouter(prefix="/sites", tags=["sites"])


# ------------------------------------------------------------------
# Helpers de conversion géométrie <-> lat/lon
# (jamais de coordonnées inventées : None si geom est NULL — section 74)
# ------------------------------------------------------------------
def _geom_to_latlon(geom) -> tuple[float | None, float | None]:
    if geom is None:
        return None, None
    point = to_shape(geom)
    return point.y, point.x  # lat, lon


def _site_to_out(site: Site) -> SiteOut:
    lat, lon = _geom_to_latlon(site.geom)
    return SiteOut(
        id=site.id,
        code=site.code,
        previous_codes=site.previous_codes or [],
        name=site.name,
        wilaya_id=site.wilaya_id,
        commune_id=site.commune_id,
        address=site.address,
        latitude=lat,
        longitude=lon,
        site_type=site.site_type,
        owner_name=site.owner_name,
        organisme=site.organisme,
        status_id=site.status_id,
        priority=site.priority,
        responsible_user_id=site.responsible_user_id,
        secondary_responsible_user_id=site.secondary_responsible_user_id,
        next_action=site.next_action,
        observation=site.observation,
        is_favorite=site.is_favorite,
        custom_fields=site.custom_fields or {},
        created_at=site.created_at,
        updated_at=site.updated_at,
    )


def _site_to_list_item(site: Site) -> SiteListItem:
    lat, lon = _geom_to_latlon(site.geom)
    return SiteListItem(
        id=site.id,
        code=site.code,
        name=site.name,
        wilaya_id=site.wilaya_id,
        status_id=site.status_id,
        priority=site.priority,
        latitude=lat,
        longitude=lon,
        is_favorite=site.is_favorite,
    )


async def _get_site_or_404(db: AsyncSession, site_id: uuid.UUID, include_deleted: bool = False) -> Site:
    stmt = select(Site).where(Site.id == site_id)
    if not include_deleted:
        stmt = stmt.where(Site.deleted_at.is_(None))
    result = await db.execute(stmt)
    site = result.scalar_one_or_none()
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site introuvable")
    return site


async def _assert_code_unique(db: AsyncSession, code: str, exclude_site_id: uuid.UUID | None = None) -> None:
    stmt = select(Site.id).where(Site.code == code)
    if exclude_site_id:
        stmt = stmt.where(Site.id != exclude_site_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Le code '{code}' est déjà utilisé par un autre site",
        )


# ------------------------------------------------------------------
# CRUD
# ------------------------------------------------------------------
@router.post("", response_model=SiteOut, status_code=status.HTTP_201_CREATED)
async def create_site(
    payload: SiteCreate,
    current_user: User = Depends(require_permission("sites", "write")),
    db: AsyncSession = Depends(get_db),
) -> SiteOut:
    await _assert_code_unique(db, payload.code)

    now = datetime.now(timezone.utc)
    site = Site(
        code=payload.code,
        name=payload.name,
        wilaya_id=payload.wilaya_id,
        commune_id=payload.commune_id,
        address=payload.address,
        geom=f"SRID=4326;POINT({payload.longitude} {payload.latitude})"
        if payload.latitude is not None and payload.longitude is not None
        else None,
        site_type=payload.site_type,
        owner_name=payload.owner_name,
        organisme=payload.organisme,
        status_id=payload.status_id,
        priority=payload.priority or 2,
        responsible_user_id=payload.responsible_user_id,
        secondary_responsible_user_id=payload.secondary_responsible_user_id,
        next_action=payload.next_action,
        observation=payload.observation,
        is_favorite=bool(payload.is_favorite),
        custom_fields=payload.custom_fields or {},
        created_by=current_user.id,
        updated_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(site)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Code déjà existant") from exc

    await log_audit(
        db, user_id=current_user.id, entity="sites", entity_id=site.id,
        action="CREATE", new_value=site.code,
    )
    await db.commit()
    await db.refresh(site)
    return _site_to_out(site)


@router.get("", response_model=SiteListResponse)
async def list_sites(
    wilaya_id: int | None = None,
    status_id: int | None = None,
    responsible_user_id: uuid.UUID | None = None,
    q: str | None = Query(None, description="Recherche : code, nom, propriétaire, organisme"),
    favorites_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SiteListResponse:
    stmt = select(Site).where(Site.deleted_at.is_(None))
    count_stmt = select(func.count()).select_from(Site).where(Site.deleted_at.is_(None))

    if wilaya_id is not None:
        stmt = stmt.where(Site.wilaya_id == wilaya_id)
        count_stmt = count_stmt.where(Site.wilaya_id == wilaya_id)
    if status_id is not None:
        stmt = stmt.where(Site.status_id == status_id)
        count_stmt = count_stmt.where(Site.status_id == status_id)
    if responsible_user_id is not None:
        stmt = stmt.where(Site.responsible_user_id == responsible_user_id)
        count_stmt = count_stmt.where(Site.responsible_user_id == responsible_user_id)
    if favorites_only:
        stmt = stmt.where(Site.is_favorite.is_(True))
        count_stmt = count_stmt.where(Site.is_favorite.is_(True))
    if q:
        pattern = f"%{q}%"
        search_filter = (
            Site.code.ilike(pattern)
            | Site.name.ilike(pattern)
            | Site.owner_name.ilike(pattern)
            | Site.organisme.ilike(pattern)
        )
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)

    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(Site.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    sites = result.scalars().all()

    return SiteListResponse(
        items=[_site_to_list_item(s) for s in sites],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/trash", response_model=list[SiteOut])
async def list_trash(
    current_user: User = Depends(require_permission("sites", "write")),
    db: AsyncSession = Depends(get_db),
) -> list[SiteOut]:
    """Corbeille — section 18."""
    result = await db.execute(select(Site).where(Site.deleted_at.is_not(None)))
    return [_site_to_out(s) for s in result.scalars().all()]


@router.get("/{site_id}", response_model=SiteOut)
async def get_site(
    site_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SiteOut:
    site = await _get_site_or_404(db, site_id)
    return _site_to_out(site)


@router.patch("/{site_id}", response_model=SiteOut)
async def update_site(
    site_id: uuid.UUID,
    payload: SiteUpdate,
    current_user: User = Depends(require_permission("sites", "write")),
    db: AsyncSession = Depends(get_db),
) -> SiteOut:
    site = await _get_site_or_404(db, site_id)
    changes = payload.model_dump(exclude_unset=True)

    # Le changement de code suit une route dédiée avec confirmation (section 17)
    if "code" in changes and changes["code"] != site.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Utilisez PATCH /sites/{id}/code pour changer le code (confirmation requise)",
        )
    changes.pop("code", None)

    lat = changes.pop("latitude", None) if "latitude" in changes else "unset"
    lon = changes.pop("longitude", None) if "longitude" in changes else "unset"
    if lat != "unset" or lon != "unset":
        new_lat = lat if lat != "unset" else _geom_to_latlon(site.geom)[0]
        new_lon = lon if lon != "unset" else _geom_to_latlon(site.geom)[1]
        site.geom = (
            f"SRID=4326;POINT({new_lon} {new_lat})" if new_lat is not None and new_lon is not None else None
        )

    for field, new_value in changes.items():
        old_value = getattr(site, field)
        if old_value != new_value:
            await log_audit(
                db, user_id=current_user.id, entity="sites", entity_id=site.id,
                action="UPDATE", field=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
            )
            setattr(site, field, new_value)

    site.updated_by = current_user.id
    site.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(site)
    return _site_to_out(site)


@router.patch("/{site_id}/code", response_model=SiteOut)
async def change_site_code(
    site_id: uuid.UUID,
    payload: CodeChangeConfirm,
    current_user: User = Depends(require_permission("sites", "write")),
    db: AsyncSession = Depends(get_db),
) -> SiteOut:
    """Changement de code avec vérification d'unicité + confirmation explicite
    + conservation de l'ancien code dans l'historique (section 17)."""
    site = await _get_site_or_404(db, site_id)

    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation requise (confirm=true) pour changer le code d'un site",
        )

    await _assert_code_unique(db, payload.new_code, exclude_site_id=site_id)

    old_code = site.code
    site.previous_codes = [*(site.previous_codes or []), old_code]
    site.code = payload.new_code
    site.updated_by = current_user.id
    site.updated_at = datetime.now(timezone.utc)

    await log_audit(
        db, user_id=current_user.id, entity="sites", entity_id=site.id,
        action="CODE_CHANGE", field="code", old_value=old_code, new_value=payload.new_code,
    )
    # Note : la mise à jour des relations (documents, contrats, contacts...) se fait
    # par site_id (clé stable), pas par code — donc rien d'autre à migrer ici.

    await db.commit()
    await db.refresh(site)
    return _site_to_out(site)


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_site(
    site_id: uuid.UUID,
    current_user: User = Depends(require_permission("sites", "write")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Suppression douce -> Corbeille (section 18). Jamais de suppression réelle ici."""
    site = await _get_site_or_404(db, site_id)
    site.deleted_at = datetime.now(timezone.utc)
    await log_audit(
        db, user_id=current_user.id, entity="sites", entity_id=site.id, action="DELETE",
    )
    await db.commit()


@router.post("/{site_id}/restore", response_model=SiteOut)
async def restore_site(
    site_id: uuid.UUID,
    current_user: User = Depends(require_permission("sites", "write")),
    db: AsyncSession = Depends(get_db),
) -> SiteOut:
    site = await _get_site_or_404(db, site_id, include_deleted=True)
    if site.deleted_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ce site n'est pas dans la corbeille")
    site.deleted_at = None
    await log_audit(
        db, user_id=current_user.id, entity="sites", entity_id=site.id, action="RESTORE",
    )
    await db.commit()
    await db.refresh(site)
    return _site_to_out(site)


@router.delete("/{site_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def permanently_delete_site(
    site_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Suppression définitive — réservée ADMIN (section 18)."""
    from app.models.user import Role  # import local pour éviter un cycle

    role_result = await db.execute(select(Role).where(Role.id == current_user.role_id))
    role = role_result.scalar_one()
    if role.code != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un ADMIN peut supprimer définitivement un site",
        )
    site = await _get_site_or_404(db, site_id, include_deleted=True)
    if site.deleted_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le site doit d'abord être dans la corbeille avant suppression définitive",
        )
    await log_audit(
        db, user_id=current_user.id, entity="sites", entity_id=site.id, action="PERMANENT_DELETE",
        old_value=site.code,
    )
    await db.delete(site)
    await db.commit()
