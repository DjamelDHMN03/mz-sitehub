"""
Service de parsing KML/KMZ -> GeoJSON (sections 23-29 du cahier des charges).

Ne dépend que de la bibliothèque standard Python (xml.etree, zipfile) —
0 DA, aucune dépendance externe pour cette brique critique.

Le KML place les coordonnées en (longitude, latitude[, altitude]) — c'est
le format GeoJSON natif, donc aucune conversion d'ordre n'est nécessaire
pour les valeurs numériques elles-mêmes, seulement leur regroupement.
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from xml.etree import ElementTree as ET

KML_NS = "{http://www.opengis.net/kml/2.2}"

# Détecte un code site type AL6328, BL0705, DJ3799, AI6020...
# (2 lettres majuscules + 3 à 5 chiffres), dans le nom de l'objet ou du fichier.
# Lookarounds plutôt que \b : \b ne coupe pas avant "_" (word char en regex),
# ce qui ratait par exemple "AL6328_TSS.kmz" avec une frontière \b classique.
SITE_CODE_PATTERN = re.compile(r"(?<![A-Z0-9])([A-Z]{2}\d{3,5})(?!\d)")


@dataclass
class ParsedFeature:
    name: str | None
    description: str | None
    geometry_type: str  # Point, LineString, Polygon, MultiGeometry...
    coordinates: list  # structure GeoJSON-compatible selon le type
    style: dict | None = field(default=None)
    detected_code: str | None = None

    def to_geojson_feature(self) -> dict:
        return {
            "type": "Feature",
            "properties": {
                "name": self.name,
                "description": self.description,
                "detected_code": self.detected_code,
                "style": self.style,
            },
            "geometry": {
                "type": self.geometry_type,
                "coordinates": self.coordinates,
            },
        }


class KmlParseError(Exception):
    pass


def detect_site_code(*texts: str | None) -> str | None:
    """Cherche un code site dans une série de textes (nom objet, description,
    nom de fichier...), dans l'ordre donné. Renvoie le premier trouvé."""
    for text in texts:
        if not text:
            continue
        match = SITE_CODE_PATTERN.search(text.upper())
        if match:
            return match.group(1)
    return None


def _parse_coords_text(text: str) -> list[list[float]]:
    """Parse une chaîne <coordinates> KML : 'lon,lat,alt lon,lat,alt ...'
    (séparateurs espace/retour à la ligne entre points, virgule entre valeurs)."""
    points = []
    for chunk in text.split():
        parts = chunk.split(",")
        if len(parts) < 2:
            continue
        lon, lat = float(parts[0]), float(parts[1])
        points.append([lon, lat])
    return points


def _parse_geometry(geom_el: ET.Element) -> tuple[str, list] | None:
    tag = geom_el.tag.replace(KML_NS, "")

    if tag == "Point":
        coords_el = geom_el.find(f"{KML_NS}coordinates")
        if coords_el is None or not coords_el.text:
            return None
        points = _parse_coords_text(coords_el.text)
        if not points:
            return None
        return "Point", points[0]

    if tag == "LineString":
        coords_el = geom_el.find(f"{KML_NS}coordinates")
        if coords_el is None or not coords_el.text:
            return None
        return "LineString", _parse_coords_text(coords_el.text)

    if tag == "Polygon":
        outer_el = geom_el.find(
            f"{KML_NS}outerBoundaryIs/{KML_NS}LinearRing/{KML_NS}coordinates"
        )
        if outer_el is None or not outer_el.text:
            return None
        rings = [_parse_coords_text(outer_el.text)]
        for inner_el in geom_el.findall(
            f"{KML_NS}innerBoundaryIs/{KML_NS}LinearRing/{KML_NS}coordinates"
        ):
            if inner_el.text:
                rings.append(_parse_coords_text(inner_el.text))
        return "Polygon", rings

    if tag == "MultiGeometry":
        sub_geometries = []
        sub_types = set()
        for child in geom_el:
            parsed = _parse_geometry(child)
            if parsed:
                sub_type, sub_coords = parsed
                sub_types.add(sub_type)
                sub_geometries.append(sub_coords)
        if not sub_geometries:
            return None
        # Si tous les sous-éléments sont du même type, on peut être plus précis
        # (MultiPoint / MultiLineString / MultiPolygon) sinon GeometryCollection générique.
        if len(sub_types) == 1:
            single_type = next(iter(sub_types))
            return f"Multi{single_type}", sub_geometries
        return "MultiGeometry", sub_geometries

    return None  # géométrie non supportée, ignorée sans faire planter le reste


def _parse_style(placemark_el: ET.Element) -> dict | None:
    """Lit un style inline simple (couleur/épaisseur) s'il est présent
    directement sur le Placemark (section 26). Les styles référencés par
    <styleUrl> vers un <Style> global ne sont pas résolus dans cette version
    — limitation connue, à traiter si un fichier réel en a besoin."""
    style_el = placemark_el.find(f"{KML_NS}Style")
    if style_el is None:
        return None

    result: dict = {}
    line_style = style_el.find(f"{KML_NS}LineStyle")
    if line_style is not None:
        color_el = line_style.find(f"{KML_NS}color")
        width_el = line_style.find(f"{KML_NS}width")
        if color_el is not None and color_el.text:
            result["line_color"] = color_el.text
        if width_el is not None and width_el.text:
            result["line_width"] = float(width_el.text)

    poly_style = style_el.find(f"{KML_NS}PolyStyle")
    if poly_style is not None:
        color_el = poly_style.find(f"{KML_NS}color")
        if color_el is not None and color_el.text:
            result["fill_color"] = color_el.text

    return result or None


def parse_kml_bytes(data: bytes, filename: str | None = None) -> list[ParsedFeature]:
    """Parse un fichier KML brut et renvoie la liste des features extraites.
    Ne lève pas d'exception sur une géométrie individuelle invalide : elle est
    simplement ignorée, pour ne pas bloquer l'import du reste du fichier."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise KmlParseError(f"Fichier KML invalide : {exc}") from exc

    features: list[ParsedFeature] = []

    for placemark in root.iter(f"{KML_NS}Placemark"):
        name_el = placemark.find(f"{KML_NS}name")
        desc_el = placemark.find(f"{KML_NS}description")
        name = name_el.text.strip() if name_el is not None and name_el.text else None
        description = desc_el.text.strip() if desc_el is not None and desc_el.text else None

        geometry = None
        for child in placemark:
            tag = child.tag.replace(KML_NS, "")
            if tag in ("Point", "LineString", "Polygon", "MultiGeometry"):
                geometry = _parse_geometry(child)
                break

        if geometry is None:
            continue  # Placemark sans géométrie exploitable — ignoré

        geometry_type, coordinates = geometry
        detected_code = detect_site_code(name, description, filename)

        features.append(
            ParsedFeature(
                name=name,
                description=description,
                geometry_type=geometry_type,
                coordinates=coordinates,
                style=_parse_style(placemark),
                detected_code=detected_code,
            )
        )

    return features


def parse_kmz_bytes(data: bytes, filename: str | None = None) -> list[ParsedFeature]:
    """Décompresse un KMZ, trouve le premier .kml à l'intérieur, le parse."""
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            kml_names = [n for n in archive.namelist() if n.lower().endswith(".kml")]
            if not kml_names:
                raise KmlParseError("Aucun fichier .kml trouvé dans l'archive KMZ")
            # Convention : doc.kml est généralement le fichier principal.
            kml_names.sort(key=lambda n: (n.lower() != "doc.kml", n))
            kml_data = archive.read(kml_names[0])
    except zipfile.BadZipFile as exc:
        raise KmlParseError(f"Fichier KMZ invalide (pas une archive ZIP) : {exc}") from exc

    return parse_kml_bytes(kml_data, filename=filename)


def features_to_geojson(features: list[ParsedFeature]) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [f.to_geojson_feature() for f in features],
    }
