"""
Tests du service de reconnaissance de documents — bibliothèque standard uniquement.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.document_recognition import recognize_filename


def test_cahier_des_charges_example():
    """Exemple exact de la section 41 : AL6328_APS_V2.pdf -> AL6328/APS/V2."""
    r = recognize_filename("AL6328_APS_V2.pdf")
    assert r.detected_code == "AL6328"
    assert r.detected_category == "APS"
    assert r.detected_version == 2
    assert r.is_ambiguous is False


def test_tss_maps_to_aps_category():
    r = recognize_filename("AL6328_TSS.kmz")
    assert r.detected_code == "AL6328"
    assert r.detected_category == "APS"


def test_code_detected_at_end_of_filename():
    r = recognize_filename("Contrat_signe_BL0705.pdf")
    assert r.detected_code == "BL0705"
    assert r.detected_category == "CONTRATS"


def test_unrecognizable_filename_is_ambiguous():
    r = recognize_filename("document_sans_infos.pdf")
    assert r.is_ambiguous is True
    assert r.detected_code is None


def test_generic_filename_is_ambiguous():
    r = recognize_filename("scan.pdf")
    assert r.is_ambiguous is True


def test_multiple_categories_is_ambiguous():
    r = recognize_filename("AL6328_APS_CONTRAT_V1.pdf")
    assert r.is_ambiguous is True
    assert "Plusieurs catégories" in (r.ambiguity_reason or "")
