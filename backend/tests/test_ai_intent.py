"""
Tests de l'analyseur d'intention MZ ASSISTANT — bibliothèque standard
uniquement. Couvre tous les exemples EXACTS des sections 62-63 du cahier
des charges, plus des cas limites pour vérifier l'absence de faux positifs.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai import intent as I


def test_list_sites_by_status_bloques():
    r = I.parse_intent("Donne-moi tous les sites bloqués.")
    assert r.type == I.INTENT_LIST_SITES_BY_STATUS
    assert r.params["status"] == "BLOQUE"


def test_sites_missing_aps_with_wilaya():
    r = I.parse_intent("Montre-moi les sites de Blida sans APS.")
    assert r.type == I.INTENT_LIST_SITES_MISSING_APS
    assert r.params["wilaya"] == "Blida"


def test_summarize_site():
    r = I.parse_intent("Résume AL6328.")
    assert r.type == I.INTENT_SUMMARIZE_SITE
    assert r.params["code"] == "AL6328"


def test_missing_documents():
    r = I.parse_intent("Quels documents manquent pour AL6286 ?")
    assert r.type == I.INTENT_MISSING_DOCUMENTS
    assert r.params["code"] == "AL6286"


def test_contracts_expiring():
    r = I.parse_intent("Quels contrats arrivent bientôt à expiration ?")
    assert r.type == I.INTENT_CONTRACTS_EXPIRING


def test_sites_without_gps():
    r = I.parse_intent("Quels sites n'ont pas de GPS ?")
    assert r.type == I.INTENT_LIST_SITES_WITHOUT_GPS


def test_map_filter_show_status():
    r = I.parse_intent("Affiche les sites bloqués.")
    assert r.type == I.INTENT_MAP_FILTER_SHOW
    assert r.params["status"] == "BLOQUE"


def test_map_filter_show_negociation():
    r = I.parse_intent("Affiche les sites en négociation.")
    assert r.type == I.INTENT_MAP_FILTER_SHOW
    assert r.params["status"] == "NEGOCIATION"


def test_map_filter_show_wilaya():
    r = I.parse_intent("Affiche les sites de Blida.")
    assert r.type == I.INTENT_MAP_FILTER_SHOW
    assert r.params["wilaya"] == "Blida"


def test_map_filter_hide():
    r = I.parse_intent("Masque les sites opérationnels.")
    assert r.type == I.INTENT_MAP_FILTER_HIDE
    assert r.params["status"] == "OPERATIONNEL"


def test_contact_role_lookup():
    r = I.parse_intent("Qui est le DRH d'EGUVA ?")
    assert r.type == I.INTENT_CONTACT_ROLE_LOOKUP
    assert r.params["role"] == "DRH"
    assert r.params["organisme"] == "eguva"


def test_out_of_scope_returns_unknown_low_confidence():
    for text in ["Bonjour, comment ça va ?", "Peux-tu m'aider avec quelque chose de compliqué ?", ""]:
        r = I.parse_intent(text)
        assert r.type == I.INTENT_UNKNOWN
        assert r.confidence == "basse"


def test_code_extraction_in_longer_sentence():
    r = I.parse_intent("Peux-tu me faire un résumé rapide du site AL6328 s'il te plaît ?")
    assert r.type == I.INTENT_SUMMARIZE_SITE
    assert r.params["code"] == "AL6328"


def test_add_contact_action_exact_example_section_69():
    r = I.parse_intent("Ajoute BENREGREG AMEUR comme DRH de AL6328.")
    assert r.type == I.INTENT_ADD_CONTACT
    assert r.params["name"] == "BENREGREG AMEUR"
    assert r.params["role"] == "DRH"
    assert r.params["code"] == "AL6328"
