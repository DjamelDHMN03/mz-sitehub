"""
Routeur /map-layers — import KMZ/KML (sections 23-30).

Note de stockage : sauvegarde locale directe ici (STORAGE_LOCAL_PATH) en
attendant l'abstraction StorageProvider générique de la Phase 11 (GED) qui
sera alors réutilisée partout (documents, photos, couches). Pas de
duplication de logique prévue : cette fonction sera remplacée par un appel
à cette abstraction sans changer la route.
"""
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from geoalchemy2.shape import to_shape
from shapely.geometry import mapping

from app.core.audit import log_audit
from app.core.config import get_settings
from app.core.deps import get_current_user, require_permission
from app.core.upload_limits import assert_upload_size_ok
from app.db.session import get_db
from app.models.map_layer import MapFeature, MapFeatureSite, MapLayer
from app.models.site import Site, SiteStatus
from app.models.user import User
from app.schemas.map_layer import (
    ImportResult,
    LinkFeatureRequest,
    LinkSuggestion,
    MapFeatureOut,
    MapLayerOut,
)
from app.schemas.map_layer_update import MapLayerUpdate
from app.services.geometry_wkt import geojson_geometry_to_wkt
from app.services.kml_parser import KmlParseError, ParsedFeature, parse_kml_bytes, parse_kmz_bytes

router = APIRouter(prefix="/map-layers", tags=["map-layers"])
settings = get_settings()


def _save_original_file(content: bytes, filename: str) -> str:
    """Sauvegarde le fichier original tel quel (téléchargeable ensuite, section 27)."""
    layers_dir = os.path.join(settings.storage_local_path, "map_layers")
    os.makedirs(layers_dir, exist_ok=True)
    safe_name = f"{uuid.uuid4()}_{filename}"
    full_path = os.path.join(layers_dir, safe_name)
    with open(full_path, "wb") as f:
        f.write(content)
    return full_path


@router.post("/import", response_model=ImportResult, status_code=status.HTTP_201_CREATED)
async def import_map_layer(
    file: UploadFile,
    current_user: User = Depends(require_permission("sites", "write")),
    db: AsyncSession = Depends(get_db),
) -> ImportResult:
    filename = file.filename or "sans_nom"
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext not in ("kml", "kmz"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format non supporté — seuls .kml et .kmz sont acceptés pour l'instant "
            "(GeoJSON prévu, non implémenté dans cette phase)",
        )

    content = await file.read()

    try:
        assert_upload_size_ok(content)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc

    try:
        parsed_features: list[ParsedFeature] = (
            parse_kmz_bytes(content, filename=filename)
            if ext == "kmz"
            else parse_kml_bytes(content, filename=filename)
        )
    except KmlParseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not parsed_features:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune géométrie exploitable trouvée dans ce fichier",
        )

    storage_key = _save_original_file(content, filename)

    layer = MapLayer(
        name=filename.rsplit(".", 1)[0],
        source_type=ext.upper(),
        original_filename=filename,
        storage_key=storage_key,
        uploaded_by=current_user.id,
        is_visible=True,
        feature_count=len(parsed_features),
        created_at=datetime.now(timezone.utc),
    )
    db.add(layer)
    await db.flush()

    features_without_geometry = 0
    feature_outputs: list[MapFeatureOut] = []

    for pf in parsed_features:
        wkt = geojson_geometry_to_wkt(pf.geometry_type, pf.coordinates)
        if wkt is None:
            features_without_geometry += 1

        feature = MapFeature(
            layer_id=layer.id,
            name=pf.name,
            description=pf.description,
            geometry_type=pf.geometry_type,
            geom=wkt,
            style=pf.style,
            detected_code=pf.detected_code,
            raw_attributes={"raw_coordinates": pf.coordinates} if wkt is None else None,
        )
        db.add(feature)
        await db.flush()

        feature_outputs.append(
            MapFeatureOut(
                id=feature.id,
                name=feature.name,
                geometry_type=feature.geometry_type,
                detected_code=feature.detected_code,
                has_geometry=wkt is not None,
            )
        )

    await log_audit(
        db, user_id=current_user.id, entity="map_layers", entity_id=layer.id,
        action="IMPORT", new_value=f"{filename} ({len(parsed_features)} features)",
    )
    await db.commit()
    await db.refresh(layer)

    return ImportResult(
        layer=MapLayerOut.model_validate(layer),
        features=feature_outputs,
        features_without_geometry=features_without_geometry,
    )


@router.get("", response_model=list[MapLayerOut])
async def list_map_layers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MapLayerOut]:
    result = await db.execute(select(MapLayer).where(MapLayer.deleted_at.is_(None)))
    return [MapLayerOut.model_validate(l) for l in result.scalars().all()]


@router.patch("/{layer_id}", response_model=MapLayerOut)
async def update_map_layer(
    layer_id: uuid.UUID,
    payload: MapLayerUpdate,
    current_user: User = Depends(require_permission("sites", "write")),
    db: AsyncSession = Depends(get_db),
) -> MapLayerOut:
    result = await db.execute(
        select(MapLayer).where(MapLayer.id == layer_id, MapLayer.deleted_at.is_(None))
    )
    layer = result.scalar_one_or_none()
    if layer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Couche introuvable")

    if payload.name is not None:
        layer.name = payload.name
    if payload.is_visible is not None:
        layer.is_visible = payload.is_visible

    await db.commit()
    await db.refresh(layer)
    return MapLayerOut.model_validate(layer)


@router.delete("/{layer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_map_layer(
    layer_id: uuid.UUID,
    current_user: User = Depends(require_permission("sites", "write")),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(MapLayer).where(MapLayer.id == layer_id))
    layer = result.scalar_one_or_none()
    if layer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Couche introuvable")
    layer.deleted_at = datetime.now(timezone.utc)
    await log_audit(db, user_id=current_user.id, entity="map_layers", entity_id=layer.id, action="DELETE")
    await db.commit()


@router.get("/{layer_id}/features")
async def get_layer_features_geojson(
    layer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Renvoie les features d'une couche au format GeoJSON, prêtes à être
    affichées sur la carte (section 27/31). Les features sans géométrie
    convertible (MultiGeometry hétérogène — voir geometry_wkt.py) sont
    listées séparément plutôt que silencieusement ignorées."""
    result = await db.execute(select(MapFeature).where(MapFeature.layer_id == layer_id))
    features = result.scalars().all()

    geojson_features = []
    skipped = 0
    for f in features:
        if f.geom is None:
            skipped += 1
            continue
        shape = to_shape(f.geom)
        geojson_features.append(
            {
                "type": "Feature",
                "properties": {
                    "id": str(f.id),
                    "name": f.name,
                    "description": f.description,
                    "detected_code": f.detected_code,
                    "style": f.style,
                },
                "geometry": mapping(shape),
            }
        )

    return {
        "type": "FeatureCollection",
        "features": geojson_features,
        "skipped_without_geometry": skipped,
    }


@router.get("/{layer_id}/link-suggestions", response_model=list[LinkSuggestion])
async def get_link_suggestions(
    layer_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LinkSuggestion]:
    """Section 29 : pour chaque feature avec un code détecté, propose soit de
    rattacher à un site existant, soit de signaler un nouveau site."""
    result = await db.execute(
        select(MapFeature).where(
            MapFeature.layer_id == layer_id, MapFeature.detected_code.is_not(None)
        )
    )
    features = result.scalars().all()

    suggestions: list[LinkSuggestion] = []
    for feature in features:
        site_result = await db.execute(
            select(Site.id).where(Site.code == feature.detected_code, Site.deleted_at.is_(None))
        )
        existing_site_id = site_result.scalar_one_or_none()
        suggestions.append(
            LinkSuggestion(
                feature_id=feature.id,
                detected_code=feature.detected_code,
                existing_site_id=existing_site_id,
                suggestion="RATTACHER" if existing_site_id else "NOUVEAU_SITE",
            )
        )
    return suggestions


@router.post("/features/{feature_id}/link", status_code=status.HTTP_200_OK)
async def link_feature_to_site(
    feature_id: uuid.UUID,
    payload: LinkFeatureRequest,
    current_user: User = Depends(require_permission("sites", "write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(MapFeature).where(MapFeature.id == feature_id))
    feature = result.scalar_one_or_none()
    if feature is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature introuvable")

    if payload.action == "IGNORER":
        return {"status": "ignoré"}

    if payload.action == "RATTACHER":
        if payload.site_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "site_id requis pour RATTACHER")
        link = MapFeatureSite(
            map_feature_id=feature.id, site_id=payload.site_id,
            linked_by=current_user.id, linked_at=datetime.now(timezone.utc),
        )
        db.add(link)
        await db.commit()
        return {"status": "rattaché", "site_id": str(payload.site_id)}

    if payload.action == "CREER":
        if not feature.detected_code:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Impossible de créer un site sans code détecté sur cette feature",
            )
        nouveau_status = (
            await db.execute(select(SiteStatus).where(SiteStatus.code == "NOUVEAU"))
        ).scalar_one()

        now = datetime.now(timezone.utc)
        site = Site(
            code=feature.detected_code,
            name=feature.name,
            geom=feature.geom if feature.geometry_type == "Point" else None,
            status_id=nouveau_status.id,
            priority=2,
            created_by=current_user.id,
            updated_by=current_user.id,
            created_at=now,
            updated_at=now,
        )
        db.add(site)
        await db.flush()

        link = MapFeatureSite(
            map_feature_id=feature.id, site_id=site.id,
            linked_by=current_user.id, linked_at=now,
        )
        db.add(link)
        await log_audit(
            db, user_id=current_user.id, entity="sites", entity_id=site.id,
            action="CREATE_FROM_MAP_IMPORT", new_value=site.code,
        )
        await db.commit()
        return {"status": "créé", "site_id": str(site.id)}

    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Action inconnue: {payload.action}")
