"""
Tests de l'import Excel — utilisent de vrais fichiers .xlsx construits en
mémoire avec openpyxl (déjà requis pour lire du xlsx en Python).
"""
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from openpyxl import Workbook

from app.services.excel_import import (
    ExcelImportError,
    ExcelRow,
    build_sync_preview,
    detect_columns,
    parse_excel_rows,
)


def test_detect_columns_with_accents_and_variants():
    mapping = detect_columns(["Code Site", "Nom du site", "Wilaya", "Propriétaire", "Colonne Inconnue"])
    assert mapping.detected["code"] == 0
    assert mapping.detected["name"] == 1
    assert mapping.detected["wilaya"] == 2
    assert mapping.detected["owner_name"] == 3
    assert mapping.unmatched_headers == ["Colonne Inconnue"]


def _make_sample_workbook() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Code Site", "Nom du site", "Wilaya", "Propriétaire", "Statut"])
    ws.append(["AL6328", "EPIC EGUVA", "Alger", "EGUVA", "En négociation"])
    ws.append(["BL0705", "OPGI 660 logements", "Blida", "OPGI", "Bloqué"])
    ws.append([None, None, None, None, None])
    ws.append(["DJ3799", "Site Djelfa", "Djelfa", None, "Résiliation"])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_real_xlsx_ignores_empty_rows():
    _, rows = parse_excel_rows(_make_sample_workbook())
    assert len(rows) == 3
    assert [r.values["code"] for r in rows] == ["AL6328", "BL0705", "DJ3799"]


def test_sync_preview_update_create_unchanged():
    _, rows = parse_excel_rows(_make_sample_workbook())
    existing = {
        "AL6328": {"name": "EPIC EGUVA", "wilaya": "Alger", "owner_name": "EGUVA", "status": "Nouveau"},
        "BL0705": {"name": "OPGI 660 logements", "wilaya": "Blida", "owner_name": "OPGI", "status": "Bloqué"},
    }
    preview = build_sync_preview(rows, existing)

    al6328 = next(p for p in preview if p.code == "AL6328")
    assert al6328.action == "UPDATE"
    assert al6328.changes["status"] == ("Nouveau", "En négociation")

    bl0705 = next(p for p in preview if p.code == "BL0705")
    assert bl0705.action == "INCHANGE"

    dj3799 = next(p for p in preview if p.code == "DJ3799")
    assert dj3799.action == "CREATE"


def test_empty_file_raises():
    wb = Workbook()
    buf = BytesIO()
    wb.save(buf)
    with pytest.raises(ExcelImportError):
        parse_excel_rows(buf.getvalue())


def test_missing_code_column_raises():
    wb = Workbook()
    ws = wb.active
    ws.append(["Nom", "Wilaya"])
    ws.append(["Test", "Alger"])
    buf = BytesIO()
    wb.save(buf)
    with pytest.raises(ExcelImportError):
        parse_excel_rows(buf.getvalue())


def test_row_without_code_is_ignored_not_crashed():
    row = ExcelRow(row_number=99, values={"code": None, "name": "Sans code"})
    preview = build_sync_preview([row], {})
    assert preview[0].action == "IGNORE_NO_CODE"
