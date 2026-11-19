"""
Import Excel (sections 59-60).

Principe : détection automatique des colonnes par correspondance de libellés
(français, insensible à la casse/accents/espaces), puis comparaison avec les
sites existants par `code` pour classer chaque ligne en CREATE / UPDATE /
INCHANGE avant toute écriture — l'utilisateur valide après avoir vu le diff
(section 60 : "Afficher les différences avant validation").

Ne dépend que d'openpyxl (déjà nécessaire pour lire du xlsx en Python — pas
d'alternative standard) et de la bibliothèque standard.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from io import BytesIO

from openpyxl import load_workbook

# Correspondance libellé de colonne (normalisé) -> champ interne du site.
# Plusieurs libellés possibles par champ pour tolérer les variations réelles
# de fichiers Excel existants (accents, "N°" vs "No", etc.)
COLUMN_ALIASES: dict[str, list[str]] = {
    "code": ["code", "code site", "n° site", "no site", "identifiant"],
    "name": ["nom", "nom du site", "designation", "désignation"],
    "wilaya": ["wilaya"],
    "commune": ["commune"],
    "address": ["adresse"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "long", "lon"],
    "owner_name": ["proprietaire", "propriétaire"],
    "organisme": ["organisme"],
    "status": ["statut", "status"],
    "observation": ["observation", "observations", "remarque", "remarques"],
}


def _normalize(text: str) -> str:
    """minuscule, sans accents, espaces normalisés — pour matcher les
    libellés de colonnes de façon robuste."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join(text.lower().strip().split())


@dataclass
class ColumnMapping:
    detected: dict[str, int]  # champ interne -> index de colonne (0-based)
    unmatched_headers: list[str]  # colonnes du fichier non reconnues


@dataclass
class ExcelRow:
    row_number: int  # numéro de ligne dans le fichier (pour les messages d'erreur)
    values: dict[str, str | float | None]  # champ interne -> valeur brute


@dataclass
class SyncPreviewItem:
    row_number: int
    code: str | None
    action: str  # "CREATE", "UPDATE", "INCHANGE", "IGNORE_NO_CODE"
    changes: dict[str, tuple] = field(default_factory=dict)  # champ -> (ancienne, nouvelle)


class ExcelImportError(Exception):
    pass


def detect_columns(header_row: list[str]) -> ColumnMapping:
    detected: dict[str, int] = {}
    unmatched: list[str] = []

    normalized_headers = [_normalize(h) if h else "" for h in header_row]

    for field_name, aliases in COLUMN_ALIASES.items():
        normalized_aliases = [_normalize(a) for a in aliases]
        for idx, header in enumerate(normalized_headers):
            if header in normalized_aliases:
                detected[field_name] = idx
                break

    for idx, header in enumerate(header_row):
        if idx not in detected.values() and header:
            unmatched.append(header)

    return ColumnMapping(detected=detected, unmatched_headers=unmatched)


def parse_excel_rows(content: bytes) -> tuple[ColumnMapping, list[ExcelRow]]:
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:  # openpyxl lève plusieurs types selon le problème
        raise ExcelImportError(f"Fichier Excel invalide ou illisible : {exc}") from exc

    sheet = workbook.active
    rows_iter = sheet.iter_rows(values_only=True)

    try:
        header_row = [str(c).strip() if c is not None else "" for c in next(rows_iter)]
    except StopIteration:
        raise ExcelImportError("Le fichier est vide") from None

    mapping = detect_columns(header_row)
    if "code" not in mapping.detected:
        raise ExcelImportError(
            "Aucune colonne 'Code' détectée — impossible de synchroniser sans "
            "identifiant unique. Colonnes trouvées : " + ", ".join(header_row)
        )

    rows: list[ExcelRow] = []
    for row_number, raw_row in enumerate(rows_iter, start=2):  # ligne 1 = en-têtes
        if all(c is None for c in raw_row):
            continue  # ligne vide — ignorée silencieusement, pas une erreur
        values: dict[str, str | float | None] = {}
        for field_name, col_idx in mapping.detected.items():
            value = raw_row[col_idx] if col_idx < len(raw_row) else None
            if isinstance(value, str):
                value = value.strip() or None
            values[field_name] = value
        rows.append(ExcelRow(row_number=row_number, values=values))

    return mapping, rows


def build_sync_preview(
    rows: list[ExcelRow],
    existing_sites: dict[str, dict],
) -> list[SyncPreviewItem]:
    """`existing_sites` = {code: {field: valeur_actuelle}} — fourni par
    l'appelant (le routeur) après une requête DB ; cette fonction reste pure
    et testable sans base de données."""
    preview: list[SyncPreviewItem] = []

    for row in rows:
        code = row.values.get("code")
        if not code:
            preview.append(SyncPreviewItem(row_number=row.row_number, code=None, action="IGNORE_NO_CODE"))
            continue

        code = str(code).strip().upper()
        existing = existing_sites.get(code)

        if existing is None:
            preview.append(SyncPreviewItem(row_number=row.row_number, code=code, action="CREATE"))
            continue

        changes: dict[str, tuple] = {}
        for field_name, new_value in row.values.items():
            if field_name == "code":
                continue
            old_value = existing.get(field_name)
            # Comparaison tolérante : None et "" sont équivalents (case vide Excel)
            normalized_new = new_value if new_value not in (None, "") else None
            normalized_old = old_value if old_value not in (None, "") else None
            if normalized_new is not None and normalized_new != normalized_old:
                changes[field_name] = (old_value, new_value)

        action = "UPDATE" if changes else "INCHANGE"
        preview.append(SyncPreviewItem(row_number=row.row_number, code=code, action=action, changes=changes))

    return preview
