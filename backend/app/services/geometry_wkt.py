"""
Convertit les géométries extraites par kml_parser.py (format GeoJSON-like)
en WKT PostGIS, pour insertion dans `map_features.geom`.

Limitation assumée : un MultiGeometry KML hétérogène (ex. un Point + une
LineString dans le même Placemark) n'a pas de type WKT unique standard côté
GeometryCollection sans reconstruire le typage de chaque sous-élément — non
supporté dans cette version. La feature est quand même importée (nom,
description, style, code détecté) mais sans géométrie exploitable sur la
carte (`geom = NULL`), plutôt que de générer un WKT invalide ou approximatif.
"""


def _ring_to_wkt(ring: list[list[float]]) -> str:
    return "(" + ", ".join(f"{lon} {lat}" for lon, lat in ring) + ")"


def geojson_geometry_to_wkt(geometry_type: str, coordinates) -> str | None:
    if geometry_type == "Point":
        lon, lat = coordinates
        return f"SRID=4326;POINT({lon} {lat})"

    if geometry_type == "LineString":
        points = ", ".join(f"{lon} {lat}" for lon, lat in coordinates)
        return f"SRID=4326;LINESTRING({points})"

    if geometry_type == "Polygon":
        rings = ", ".join(_ring_to_wkt(ring) for ring in coordinates)
        return f"SRID=4326;POLYGON({rings})"

    if geometry_type == "MultiPoint":
        points = ", ".join(f"({lon} {lat})" for lon, lat in coordinates)
        return f"SRID=4326;MULTIPOINT({points})"

    if geometry_type == "MultiLineString":
        lines = ", ".join(
            "(" + ", ".join(f"{lon} {lat}" for lon, lat in line) + ")" for line in coordinates
        )
        return f"SRID=4326;MULTILINESTRING({lines})"

    if geometry_type == "MultiPolygon":
        polygons = ", ".join(
            "(" + ", ".join(_ring_to_wkt(ring) for ring in polygon) + ")" for polygon in coordinates
        )
        return f"SRID=4326;MULTIPOLYGON({polygons})"

    return None  # MultiGeometry hétérogène ou type non supporté — voir docstring
