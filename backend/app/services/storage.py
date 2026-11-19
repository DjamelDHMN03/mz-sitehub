"""
Abstraction de stockage documentaire (section 90-92 : migration future sans
réécriture). Tous les modules qui stockent des fichiers (Documents, Photos,
couches cartographiques) passent par `get_storage_provider()` plutôt que
d'écrire directement sur le disque — un seul endroit à changer pour brancher
Supabase Storage plus tard (STORAGE_DRIVER=supabase dans .env).
"""
from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import get_settings


class StorageProvider(ABC):
    @abstractmethod
    def save(self, content: bytes, relative_path: str) -> str:
        """Sauvegarde le contenu, renvoie la storage_key à conserver en base."""

    @abstractmethod
    def read(self, storage_key: str) -> bytes:
        """Relit le contenu à partir d'une storage_key."""

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Supprime le fichier (utilisé uniquement lors d'une suppression
        définitive — le soft delete ne touche jamais le fichier physique)."""

    @abstractmethod
    def exists(self, storage_key: str) -> bool: ...


class LocalStorageProvider(StorageProvider):
    """Implémentation par défaut — 0 DA, aucun service externe requis."""

    def __init__(self, base_path: str):
        self.base_path = base_path

    def _full_path(self, relative_path: str) -> str:
        # normpath + vérification anti path-traversal (sécurité — section 82/83)
        full = os.path.normpath(os.path.join(self.base_path, relative_path))
        if not full.startswith(os.path.normpath(self.base_path)):
            raise ValueError("Chemin de stockage invalide (tentative de sortie du dossier)")
        return full

    def save(self, content: bytes, relative_path: str) -> str:
        full_path = self._full_path(relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(content)
        return relative_path  # la storage_key = chemin relatif, portable

    def read(self, storage_key: str) -> bytes:
        with open(self._full_path(storage_key), "rb") as f:
            return f.read()

    def delete(self, storage_key: str) -> None:
        full_path = self._full_path(storage_key)
        if os.path.exists(full_path):
            os.remove(full_path)

    def exists(self, storage_key: str) -> bool:
        return os.path.exists(self._full_path(storage_key))


class SupabaseStorageProvider(StorageProvider):
    """Squelette prêt pour la Phase 24 (déploiement) si une clé Supabase est
    fournie — non implémenté tant qu'aucune clé n'est configurée (section 68 :
    aucun service payant/externe activé sans ajout explicite d'identifiants)."""

    def __init__(self, url: str, service_key: str, bucket: str):
        self.url = url
        self.service_key = service_key
        self.bucket = bucket

    def save(self, content: bytes, relative_path: str) -> str:
        raise NotImplementedError(
            "SupabaseStorageProvider non implémenté — à construire quand une "
            "clé SUPABASE_SERVICE_KEY sera réellement fournie (section 68)"
        )

    def read(self, storage_key: str) -> bytes:
        raise NotImplementedError

    def delete(self, storage_key: str) -> None:
        raise NotImplementedError

    def exists(self, storage_key: str) -> bool:
        raise NotImplementedError


@lru_cache
def get_storage_provider() -> StorageProvider:
    settings = get_settings()
    if settings.storage_driver == "supabase":
        if not settings.supabase_url or not settings.supabase_service_key:
            raise RuntimeError(
                "STORAGE_DRIVER=supabase mais SUPABASE_URL/SUPABASE_SERVICE_KEY "
                "ne sont pas renseignées dans .env"
            )
        return SupabaseStorageProvider(
            settings.supabase_url, settings.supabase_service_key, settings.supabase_bucket
        )
    return LocalStorageProvider(settings.storage_local_path)


def make_relative_path(site_code: str, category: str, filename: str) -> str:
    """Construit le chemin relatif respectant l'arborescence GED par site
    (section 39) : SITE_CODE/CATEGORIE/uuid_nomfichier"""
    safe_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
    return os.path.join(site_code, category, safe_filename)
