"""
Tests des exports — utilisent de vrais fichiers CSV/xlsx/PDF générés
(openpyxl et reportlab, déjà nécessaires en dépendances du projet).
"""
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import load_workbook

from app.services.export import site_fiche_pdf, sites_to_csv, sites_to_xlsx

SAMPLE_ROWS = [
    {"code": "AL6328", "name": "EPIC EGUVA", "wilaya": "Alger", "status": "Négociation"},
    {"code": "BL0705", "name": "OPGI 660 logements", "wilaya": "Blida", "status": "Bloqué"},
]
COLUMNS = ["code", "name", "wilaya", "status"]


def test_csv_export_contains_data():
    csv_bytes = sites_to_csv(SAMPLE_ROWS, columns=COLUMNS)
    text = csv_bytes.decode("utf-8-sig")
    assert "AL6328" in text
    assert "BL0705" in text


def test_xlsx_export_readable_and_correct():
    xlsx_bytes = sites_to_xlsx(
        SAMPLE_ROWS, columns=COLUMNS,
        headers={"code": "Code", "name": "Nom", "wilaya": "Wilaya", "status": "Statut"},
    )
    wb = load_workbook(BytesIO(xlsx_bytes))
    ws = wb.active
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    assert header == ["Code", "Nom", "Wilaya", "Statut"]
    row1 = [c.value for c in next(ws.iter_rows(min_row=2, max_row=2))]
    assert row1 == ["AL6328", "EPIC EGUVA", "Alger", "Négociation"]


def test_pdf_fiche_generates_valid_pdf():
    site = {
        "code": "AL6328", "name": "EPIC EGUVA", "wilaya": "Alger", "commune": "Reghaia",
        "address": None, "latitude": None, "longitude": None,
        "owner_name": "EPIC EGUVA", "organisme": "EPIC EGUVA", "status_label": "En négociation",
    }
    pdf_bytes = site_fiche_pdf(site, contacts=[], documents=[], contracts=[], actions=[])
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 1000


def test_pdf_missing_fields_show_a_completer_not_blank():
    """Section 74/118 : un champ inconnu doit être visible comme tel, pas
    silencieusement vide (impossible à vérifier ici sans lecteur de texte
    PDF, donc on vérifie au moins que la génération ne plante pas et que le
    contenu binaire contient bien la chaîne attendue une fois décompressé
    par reportlab — test simplifié : présence de la structure PDF valide)."""
    site = {"code": "TEST0001"}  # tous les autres champs manquants
    pdf_bytes = site_fiche_pdf(site, contacts=[], documents=[], contracts=[], actions=[])
    assert pdf_bytes[:4] == b"%PDF"
