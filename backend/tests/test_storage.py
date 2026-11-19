"""
Tests de l'abstraction de stockage (LocalStorageProvider) — bibliothèque
standard uniquement, aucune dépendance externe requise.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app.services.storage import LocalStorageProvider, make_relative_path


def test_make_relative_path_structure():
    rel_path = make_relative_path("AL6328", "APS", "AL6328_APS_V2.pdf")
    assert rel_path.startswith("AL6328")
    assert "APS" in rel_path
    assert rel_path.endswith("AL6328_APS_V2.pdf")


def test_save_read_delete_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        provider = LocalStorageProvider(tmp)
        rel_path = make_relative_path("AL6328", "APS", "test.pdf")

        key = provider.save(b"contenu de test", rel_path)
        assert provider.exists(key)
        assert provider.read(key) == b"contenu de test"

        provider.delete(key)
        assert not provider.exists(key)


def test_path_traversal_blocked():
    with tempfile.TemporaryDirectory() as tmp:
        provider = LocalStorageProvider(tmp)
        with pytest.raises(ValueError):
            provider.save(b"malveillant", "../../../etc/passwd")
