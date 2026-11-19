"""
Service de partage documentaire (sections 44-51).

- Token opaque non devinable (jamais l'URL de storage réelle — section 51)
- Calcul d'expiration à partir des options standard (24h/7j/30j/personnalisé)
- Empaquetage ZIP en mémoire pour le partage multiple (section 49)
"""
from __future__ import annotations

import secrets
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO

EXPIRY_PRESETS = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


def generate_share_token() -> str:
    """32 octets d'entropie encodés en URL-safe base64 — non devinable par force brute."""
    return secrets.token_urlsafe(32)


def compute_expiry(preset: str | None, custom: datetime | None = None) -> datetime | None:
    """`preset` in {"24h","7d","30d","custom",None}. `None` = pas d'expiration
    (usage déconseillé mais permis, ex. lien interne permanent)."""
    if preset == "custom":
        if custom is None:
            raise ValueError("Une date d'expiration personnalisée est requise avec preset='custom'")
        return custom
    if preset in EXPIRY_PRESETS:
        return datetime.now(timezone.utc) + EXPIRY_PRESETS[preset]
    if preset is None:
        return None
    raise ValueError(f"Preset d'expiration invalide : {preset}")


def is_link_valid(expires_at: datetime | None, is_revoked: bool) -> tuple[bool, str | None]:
    """Renvoie (valide, raison_si_invalide)."""
    if is_revoked:
        return False, "Ce lien a été révoqué"
    if expires_at is not None and datetime.now(timezone.utc) > expires_at:
        return False, "Ce lien a expiré"
    return True, None


def build_zip_archive(files: list[tuple[str, bytes]]) -> bytes:
    """`files` = [(nom_affiché, contenu), ...]. Gère les doublons de nom en
    suffixant (1), (2)... pour ne jamais écraser une entrée dans le ZIP."""
    buffer = BytesIO()
    used_names: dict[str, int] = {}

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for filename, content in files:
            final_name = filename
            if final_name in used_names:
                used_names[final_name] += 1
                stem, _, ext = filename.rpartition(".")
                final_name = f"{stem} ({used_names[filename]}).{ext}" if ext else f"{filename} ({used_names[filename]})"
            else:
                used_names[final_name] = 0
            archive.writestr(final_name, content)

    return buffer.getvalue()
