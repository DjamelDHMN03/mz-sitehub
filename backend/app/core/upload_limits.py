"""
Limites de sécurité partagées (section 82 : contrôle des uploads).

Centralisé ici plutôt que dupliqué dans chaque routeur — l'audit de la
Phase 21 a trouvé que seul `documents.py` avait une limite explicite,
`map_layers.py` (KMZ/KML) et `excel_import.py` n'en avaient aucune.
"""
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50 Mo, cohérent avec la GED (section 40)


def assert_upload_size_ok(content: bytes) -> None:
    """Lève ValueError si le fichier dépasse la limite — à l'appelant de
    convertir en HTTPException (garde ce module libre de FastAPI, testable
    sans dépendance)."""
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise ValueError(f"Fichier trop volumineux (max {MAX_UPLOAD_SIZE_BYTES // (1024*1024)} Mo)")
