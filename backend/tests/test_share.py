"""
Tests du service de partage — bibliothèque standard uniquement.
"""
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app.services.share import build_zip_archive, compute_expiry, generate_share_token, is_link_valid


def test_tokens_are_unique_and_long():
    t1, t2 = generate_share_token(), generate_share_token()
    assert t1 != t2
    assert len(t1) >= 32


def test_expiry_presets():
    now = datetime.now(timezone.utc)
    assert now < compute_expiry("24h") < now + timedelta(hours=25)
    assert now + timedelta(days=29) < compute_expiry("30d")
    assert compute_expiry(None) is None


def test_expiry_custom():
    custom = datetime.now(timezone.utc) + timedelta(days=100)
    assert compute_expiry("custom", custom) == custom


def test_expiry_custom_without_date_raises():
    with pytest.raises(ValueError):
        compute_expiry("custom", None)


def test_link_validity_revoked_wins_over_active_expiry():
    future = datetime.now(timezone.utc) + timedelta(days=1)
    valid, reason = is_link_valid(future, is_revoked=True)
    assert valid is False
    assert "révoqué" in reason


def test_link_validity_expired():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    valid, reason = is_link_valid(past, is_revoked=False)
    assert valid is False
    assert "expiré" in reason


def test_zip_archive_contents():
    zip_bytes = build_zip_archive([("a.pdf", b"1"), ("b.pdf", b"2")])
    with zipfile.ZipFile(BytesIO(zip_bytes)) as z:
        assert set(z.namelist()) == {"a.pdf", "b.pdf"}
        assert z.read("a.pdf") == b"1"


def test_zip_archive_duplicate_names_not_overwritten():
    zip_bytes = build_zip_archive([("photo.jpg", b"a"), ("photo.jpg", b"b")])
    with zipfile.ZipFile(BytesIO(zip_bytes)) as z:
        names = z.namelist()
        assert len(names) == 2
        assert names[0] != names[1]
