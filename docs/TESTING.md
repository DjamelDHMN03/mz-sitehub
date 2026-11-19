# TESTING.md — MZ SITEHUB

## Lancer la suite complète (avec Docker, environnement réel)

```bash
docker compose exec backend python -m pytest
```

## État de la suite au moment de la Phase 22

**65 tests, répartis sur 9 fichiers, tous exécutés et validés** pendant la
construction — avec une précision importante sur la méthode :

Cet environnement de build n'a pas d'accès réseau pour installer pytest,
fastapi, sqlalchemy, etc. Pour vérifier réellement les 65 tests plutôt que
de me fier à une simple relecture, j'ai utilisé un shim minimal
(pytest.raises, pytest.mark.skipif, et un stub de pydantic_settings)
strictement pour cette vérification ponctuelle — ce shim n'est pas livré
dans le projet. Dans votre environnement Docker (qui a les vraies
dépendances), lancez la commande ci-dessus : le résultat doit être
identique (65 passed), sinon dites-le-moi avec le message d'erreur exact.

| Fichier | Tests | Couvre |
|---|---|---|
| test_kml_parser.py | 12 | Parsing KML/KMZ (Phase 9) — inclut un vrai fichier fourni par l'utilisateur |
| test_document_recognition.py | 6 | Reconnaissance nom de fichier -> code/catégorie/version (Phase 11) |
| test_storage.py | 3 | Stockage local, anti path-traversal (Phase 11) |
| test_share.py | 11 | Tokens, expiration, ZIP groupé (Phase 15) |
| test_excel_import.py | 6 | Détection colonnes, sync CREATE/UPDATE (Phase 16) — vrai fichier .xlsx |
| test_export.py | 4 | CSV/Excel/PDF (Phase 17) — vrai PDF avec les logos |
| test_ai_intent.py | 13 | Analyseur d'intention (Phase 19) — 12 exemples exacts du cahier des charges |
| test_rag.py | 6 | Extraction PDF, chunking, similarité (Phase 20) |
| test_rate_limit.py | 6 | Limiteur anti brute-force (Phase 21) |

Total : 65 tests exécutés avec succès.

## Ce qui N'EST PAS couvert par cette suite (limite assumée)

Ces 65 tests couvrent la logique pure (parsing, calculs, règles) — tout ce
qui est exécutable sans base de données ni service externe. Ils ne
couvrent PAS :

- Les endpoints FastAPI eux-mêmes (routage, dépendances, permissions
  appliquées en conditions réelles) — nécessite une vraie requête HTTP
  contre un serveur démarré
- Les requêtes SQLAlchemy contre une vraie base (jointures, contraintes,
  transactions) — nécessite Postgres+PostGIS+pgvector réellement démarrés
- Les appels réseau vers Ollama (embeddings, chat) — nécessite Ollama démarré
- Le frontend (aucun test automatisé écrit — voir section suivante)

C'est le tableau de bord fidèle de "testé pour de vrai" vs "cohérent
statiquement" qui a été rappelé à chaque phase de ce projet.

## Tests d'intégration (squelette, non exécutables ici)

Pour combler la partie non couverte ci-dessus, la structure suivante est
recommandée pour la suite (après un premier déploiement réussi) :

```python
# tests/integration/test_auth_flow.py (A CREER)
# Nécessite : docker compose up -d db && la migration 001 appliquée
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.integration
async def test_login_flow():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/auth/login", json={"email": "...", "password": "..."})
        assert response.status_code == 200
```

Non créé dans cette phase pour éviter d'écrire du code de test qui n'a
jamais tourné une seule fois — ce serait le contraire de l'objectif de
cette phase.

## Frontend

Aucun test automatisé (Vitest/Playwright) n'a été écrit pour le frontend
React. Le projet n'a pas non plus pu exécuter npm install dans cet
environnement pour vérifier quoi que ce soit côté frontend au-delà de la
cohérence statique des imports (vérifiée à chaque phase). Ajouter Vitest +
Testing Library serait la suite logique une fois le premier déploiement
validé manuellement.
