"""
Tests du parser KML/KMZ — n'utilisent que la bibliothèque standard, donc
exécutables avec `python -m pytest tests/test_kml_parser.py` sans même
installer les dépendances du projet.

Le premier test charge le VRAI fichier fourni par l'utilisateur
(section 88 : "Créer des fichiers de test réels KMZ/KML").
"""
import sys
import zipfile
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app.services.kml_parser import (
    KmlParseError,
    detect_site_code,
    features_to_geojson,
    parse_kml_bytes,
    parse_kmz_bytes,
)

_fixture_candidate = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "exemple_reel_25_sites.kml"
REAL_KML_SAMPLE = (
    _fixture_candidate
    if _fixture_candidate.exists()
    else Path("/mnt/user-data/uploads/1788301498074_Coordonnees_GPS_STRATEGIC.kml")
)


@pytest.mark.skipif(not REAL_KML_SAMPLE.exists(), reason="fichier d'exemple non disponible")
def test_real_user_file_all_points_detected():
    data = REAL_KML_SAMPLE.read_bytes()
    features = parse_kml_bytes(data, filename=REAL_KML_SAMPLE.name)

    assert len(features) == 25
    assert all(f.geometry_type == "Point" for f in features)
    assert all(f.detected_code == f.name for f in features)

    known_codes = {"AL0099", "BL0705", "DJ3799"}
    assert known_codes.issubset({f.detected_code for f in features})


@pytest.mark.skipif(not REAL_KML_SAMPLE.exists(), reason="fichier d'exemple non disponible")
def test_real_user_file_coordinate_order():
    data = REAL_KML_SAMPLE.read_bytes()
    features = parse_kml_bytes(data)
    ai = next(f for f in features if f.name == "AI6020")
    lon, lat = ai.coordinates
    assert abs(lon - 2.24700805555556) < 1e-9
    assert abs(lat - 36.2698497222222) < 1e-9


def test_linestring():
    kml = b"""<?xml version="1.0"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
    <Placemark><name>Route AL6328</name>
    <LineString><coordinates>2.1,36.1,0 2.2,36.2,0 2.3,36.3,0</coordinates></LineString>
    </Placemark></Document></kml>"""
    features = parse_kml_bytes(kml)
    assert len(features) == 1
    assert features[0].geometry_type == "LineString"
    assert features[0].coordinates == [[2.1, 36.1], [2.2, 36.2], [2.3, 36.3]]
    assert features[0].detected_code == "AL6328"


def test_polygon_with_hole():
    kml = b"""<?xml version="1.0"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
    <Placemark><name>Zone BL0705</name>
    <Polygon>
    <outerBoundaryIs><LinearRing><coordinates>0,0,0 0,10,0 10,10,0 10,0,0 0,0,0</coordinates></LinearRing></outerBoundaryIs>
    <innerBoundaryIs><LinearRing><coordinates>2,2,0 2,4,0 4,4,0 4,2,0 2,2,0</coordinates></LinearRing></innerBoundaryIs>
    </Polygon>
    </Placemark></Document></kml>"""
    features = parse_kml_bytes(kml)
    assert features[0].geometry_type == "Polygon"
    assert len(features[0].coordinates) == 2
    assert len(features[0].coordinates[0]) == 5
    assert len(features[0].coordinates[1]) == 5


def test_multigeometry_homogeneous_points():
    kml = b"""<?xml version="1.0"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
    <Placemark><name>Groupe</name>
    <MultiGeometry>
    <Point><coordinates>1,1,0</coordinates></Point>
    <Point><coordinates>2,2,0</coordinates></Point>
    </MultiGeometry>
    </Placemark></Document></kml>"""
    features = parse_kml_bytes(kml)
    assert features[0].geometry_type == "MultiPoint"
    assert features[0].coordinates == [[1, 1], [2, 2]]


def test_kmz_extraction():
    inner_kml = (
        b'<?xml version="1.0"?><kml xmlns="http://www.opengis.net/kml/2.2">'
        b"<Document><Placemark><name>Route AL6328</name>"
        b"<LineString><coordinates>2.1,36.1,0 2.2,36.2,0</coordinates></LineString>"
        b"</Placemark></Document></kml>"
    )
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("doc.kml", inner_kml.decode())

    features = parse_kmz_bytes(buf.getvalue(), filename="AL6328_TSS.kmz")
    assert len(features) == 1
    assert features[0].geometry_type == "LineString"


def test_detect_code_from_filename_with_underscore():
    """Régression : \\b ne coupe pas avant '_' (word char en regex)."""
    assert detect_site_code(None, None, "AL6328_TSS.kmz") == "AL6328"
    assert detect_site_code(None, None, "al6328_tss.KMZ") == "AL6328"


def test_detect_code_in_sentence():
    assert detect_site_code("Route AL6328 - accès nord") == "AL6328"


def test_detect_code_no_false_positive():
    assert detect_site_code("REF123456789") is None


def test_invalid_kml_raises():
    with pytest.raises(KmlParseError):
        parse_kml_bytes(b"ceci n'est pas du xml")


def test_invalid_kmz_raises():
    with pytest.raises(KmlParseError):
        parse_kmz_bytes(b"pas un zip")


def test_geojson_conversion():
    kml = b"""<?xml version="1.0"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
    <Placemark><name>AL6328</name>
    <Point><coordinates>2.1,36.1,0</coordinates></Point>
    </Placemark></Document></kml>"""
    features = parse_kml_bytes(kml)
    geojson = features_to_geojson(features)
    assert geojson["type"] == "FeatureCollection"
    assert geojson["features"][0]["geometry"]["type"] == "Point"
    assert geojson["features"][0]["properties"]["detected_code"] == "AL6328"
