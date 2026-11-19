"""
Reconnaissance automatique de document depuis son nom de fichier (section 41).

Exemple du cahier des charges : "AL6328_APS_V2.pdf" -> code=AL6328, type=APS, version=2.

Principe : si le code ou la catégorie ne peuvent pas être détectés avec
confiance, la fonction renvoie `is_ambiguous=True` plutôt que de deviner —
c'est à l'appelant (le routeur) de demander confirmation à l'utilisateur
(section 41 : "Si ambigu : demander confirmation"), jamais d'inventer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

SITE_CODE_PATTERN = re.compile(r"(?<![A-Z0-9])([A-Z]{2}\d{3,5})(?!\d)")
VERSION_PATTERN = re.compile(r"[Vv](\d+)\b")

# Catégories acceptées par la table `documents.category` (migration 001).
# Chaque catégorie a des mots-clés reconnus dans le nom de fichier.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "DOC_B": ["DOCB", "DOC_B", "DOC-B"],
    "APS": ["APS", "PLAN_GC", "PLANGC", "TSS", "PLAN_STRUCTURE", "PLAN_TOITURE", "PLAN_PYLONE", "PLAN_RADIO"],
    "CONTRATS": ["CONTRAT", "CONTRACT"],
    "AUTORISATIONS": ["AUTORISATION", "AUTORISATIONS"],
    "PV": ["PV", "PROCES_VERBAL", "PROCESVERBAL"],
    "PHOTOS": ["PHOTO", "PHOTOS"],
    "CORRESPONDANCES": ["CORRESPONDANCE", "COURRIER"],
    "CARTOGRAPHIE": ["KML", "KMZ", "GEOJSON", "CARTO"],
}


@dataclass
class DocumentRecognition:
    detected_code: str | None
    detected_category: str | None
    detected_version: int | None
    is_ambiguous: bool
    ambiguity_reason: str | None = None


def recognize_filename(filename: str) -> DocumentRecognition:
    name_upper = filename.upper()
    # on retire l'extension pour éviter que ".KMZ" pollue la détection de code
    name_without_ext = re.sub(r"\.[A-Z0-9]{2,4}$", "", name_upper)

    code_match = SITE_CODE_PATTERN.search(name_without_ext)
    detected_code = code_match.group(1) if code_match else None

    version_match = VERSION_PATTERN.search(name_without_ext)
    detected_version = int(version_match.group(1)) if version_match else None

    matched_categories = [
        category
        for category, keywords in CATEGORY_KEYWORDS.items()
        if any(kw in name_without_ext for kw in keywords)
    ]

    detected_category = None
    is_ambiguous = False
    ambiguity_reason = None

    if len(matched_categories) == 1:
        detected_category = matched_categories[0]
    elif len(matched_categories) > 1:
        is_ambiguous = True
        ambiguity_reason = f"Plusieurs catégories possibles détectées : {matched_categories}"
    else:
        is_ambiguous = True
        ambiguity_reason = "Aucune catégorie reconnue dans le nom de fichier"

    if detected_code is None:
        is_ambiguous = True
        ambiguity_reason = (
            f"{ambiguity_reason} ; aucun code site détecté"
            if ambiguity_reason
            else "Aucun code site détecté dans le nom de fichier"
        )

    return DocumentRecognition(
        detected_code=detected_code,
        detected_category=detected_category,
        detected_version=detected_version,
        is_ambiguous=is_ambiguous,
        ambiguity_reason=ambiguity_reason,
    )
