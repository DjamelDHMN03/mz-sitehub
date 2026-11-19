"""
Analyseur d'intention MZ ASSISTANT (sections 62-63, 111).

Pourquoi un moteur à règles en plus du LLM : les exemples du cahier des
charges ("Donne-moi tous les sites bloqués", "Affiche les sites de Blida"...)
sont des commandes structurées récurrentes. Les reconnaître par règles
déterministes garantit qu'elles fonctionnent même :
- sans Ollama configuré/démarré (0 DA garanti dès la V1, section 68) ;
- sans dépendre de la fiabilité d'un modèle 8B sur du function-calling.

Le LLM (quand disponible) prend le relais pour les formulations qui ne
correspondent à aucune règle — mais passe TOUJOURS par les mêmes tools
déterministes pour aller chercher la donnée (jamais d'invention, section 66).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return " ".join(text.lower().strip().split())


STATUS_KEYWORDS: dict[str, str] = {
    "bloque": "BLOQUE", "bloques": "BLOQUE",
    "negociation": "NEGOCIATION", "en negociation": "NEGOCIATION",
    "operationnel": "OPERATIONNEL", "operationnels": "OPERATIONNEL",
    "refuse": "REFUSE", "refuses": "REFUSE",
    "signe": "CONTRAT_SIGNE", "signes": "CONTRAT_SIGNE",
    "nouveau": "NOUVEAU", "nouveaux": "NOUVEAU",
    "abandonne": "ABANDONNE", "abandonnes": "ABANDONNE",
}

SITE_CODE_PATTERN = re.compile(r"\b([A-Z]{2}\d{3,5})\b")


@dataclass
class Intent:
    type: str
    params: dict = field(default_factory=dict)
    confidence: str = "haute"


INTENT_LIST_SITES_BY_STATUS = "LIST_SITES_BY_STATUS"
INTENT_LIST_SITES_BY_WILAYA = "LIST_SITES_BY_WILAYA"
INTENT_LIST_SITES_WITHOUT_GPS = "LIST_SITES_WITHOUT_GPS"
INTENT_LIST_SITES_MISSING_APS = "LIST_SITES_MISSING_APS"
INTENT_SUMMARIZE_SITE = "SUMMARIZE_SITE"
INTENT_MISSING_DOCUMENTS = "MISSING_DOCUMENTS"
INTENT_CONTRACTS_EXPIRING = "CONTRACTS_EXPIRING"
INTENT_CONTACT_ROLE_LOOKUP = "CONTACT_ROLE_LOOKUP"
INTENT_MAP_FILTER_SHOW = "MAP_FILTER_SHOW"
INTENT_MAP_FILTER_HIDE = "MAP_FILTER_HIDE"
INTENT_ADD_CONTACT = "ADD_CONTACT"
INTENT_UNKNOWN = "UNKNOWN"


def parse_intent(text: str) -> Intent:
    normalized = _normalize(text)

    # --- Action avec confirmation obligatoire (section 69) :
    # "Ajoute BENREGREG AMEUR comme DRH de AL6328." ---
    action_match = re.search(
        r"ajoute\s+(.+?)\s+comme\s+([a-z]+)\s+d[e']\s*([a-z0-9]+)",
        normalized,
    )
    if action_match:
        name_part, role_part, code_part = action_match.groups()
        code_match = SITE_CODE_PATTERN.search(text.upper())
        return Intent(
            INTENT_ADD_CONTACT,
            {
                "name": name_part.strip().upper(),
                "role": role_part.strip().upper(),
                "code": code_match.group(1) if code_match else code_part.upper(),
            },
        )

    if "resume" in normalized or "resumé" in normalized:
        code_match = SITE_CODE_PATTERN.search(text.upper())
        if code_match:
            return Intent(INTENT_SUMMARIZE_SITE, {"code": code_match.group(1)})

    if "document" in normalized and ("manque" in normalized or "manquant" in normalized):
        code_match = SITE_CODE_PATTERN.search(text.upper())
        if code_match:
            return Intent(INTENT_MISSING_DOCUMENTS, {"code": code_match.group(1)})

    if "contrat" in normalized and "expir" in normalized:
        return Intent(INTENT_CONTRACTS_EXPIRING, {})

    if "gps" in normalized and ("pas" in normalized or "sans" in normalized):
        return Intent(INTENT_LIST_SITES_WITHOUT_GPS, {})

    role_match = re.search(r"\b(dg|drh|pdg|apc|opgi|ade|epic)\b", normalized)
    if role_match and ("qui est" in normalized or normalized.split()[0] == "qui"):
        org_match = re.search(r"\bd[e']\s*(.+?)[\s?]*$", normalized)
        organisme = org_match.group(1).strip() if org_match else None
        return Intent(
            INTENT_CONTACT_ROLE_LOOKUP,
            {"role": role_match.group(1).upper(), "organisme": organisme},
        )

    if "sans" in normalized and "aps" in normalized:
        wilaya_match = re.search(r"\bde\s+([a-z\-]+)\b", normalized)
        return Intent(
            INTENT_LIST_SITES_MISSING_APS,
            {"wilaya": wilaya_match.group(1).title() if wilaya_match else None},
        )

    is_map_command = normalized.startswith("affiche") or normalized.startswith("masque")
    if is_map_command:
        for keyword, status_code in STATUS_KEYWORDS.items():
            if keyword in normalized:
                intent_type = INTENT_MAP_FILTER_HIDE if normalized.startswith("masque") else INTENT_MAP_FILTER_SHOW
                return Intent(intent_type, {"status": status_code})
        wilaya_match = re.search(r"\bde\s+([a-z\-]+)\b", normalized)
        if wilaya_match:
            intent_type = INTENT_MAP_FILTER_HIDE if normalized.startswith("masque") else INTENT_MAP_FILTER_SHOW
            return Intent(intent_type, {"wilaya": wilaya_match.group(1).title()})

    for keyword, status_code in STATUS_KEYWORDS.items():
        if keyword in normalized and "site" in normalized:
            return Intent(INTENT_LIST_SITES_BY_STATUS, {"status": status_code})

    wilaya_match = re.search(r"sites?\s+de\s+([a-z\-]+)", normalized)
    if wilaya_match:
        return Intent(INTENT_LIST_SITES_BY_WILAYA, {"wilaya": wilaya_match.group(1).title()})

    return Intent(INTENT_UNKNOWN, {"raw_text": text}, confidence="basse")
