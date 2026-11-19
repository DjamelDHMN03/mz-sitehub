# Test manuel — Phase 9 (Import KMZ/KML)

Contrairement aux phases précédentes, la logique de parsing a déjà été
testée réellement (voir `docs/ROADMAP.md`). Ce qui reste à valider chez vous,
c'est le chemin complet HTTP + base de données + interface.

## 1. Test rapide en ligne de commande (avant même d'ouvrir le navigateur)

```bash
curl -X POST http://localhost:8000/map-layers/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@tests/fixtures/exemple_reel_25_sites.kml"
```
Doit renvoyer un JSON avec `"feature_count": 25` et la liste des 25 objets,
tous avec `"has_geometry": true`.

## 2. Vérifier les suggestions de rattachement

```bash
LAYER_ID="<coller l'id de la couche renvoyé à l'étape 1>"
curl http://localhost:8000/map-layers/$LAYER_ID/link-suggestions \
  -H "Authorization: Bearer $TOKEN"
```
- Si vous avez déjà créé un site avec le code `AL0099` (Phase 4), il doit
  apparaître avec `"suggestion": "RATTACHER"` et son `existing_site_id`.
- Les 24 autres codes doivent apparaître en `"NOUVEAU_SITE"` (aucun site
  correspondant n'existe encore).

## 3. Créer un site depuis une feature importée

```bash
FEATURE_ID="<un feature_id de la réponse précédente>"
curl -X POST http://localhost:8000/map-layers/features/$FEATURE_ID/link \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"action": "CREER"}'
```
Doit renvoyer `{"status": "créé", "site_id": "..."}`. Vérifiez ensuite avec
`GET /sites/{site_id}` que le site a bien les coordonnées GPS du KML
(section 21 : les sites avec GPS doivent apparaître automatiquement sur la carte).

## 4. Interface web

Ouvrez http://localhost:5173/carte/importer, glissez-déposez le fichier
`tests/fixtures/exemple_reel_25_sites.kml` — vous devez voir la liste des
25 codes avec les badges "Nouveau site détecté" / "Rattacher au site existant",
et pouvoir cliquer Créer/Ignorer/Rattacher sur chacun.

## 5. Lancer la vraie suite de tests (dans le conteneur, qui a pytest)

```bash
docker compose exec backend python -m pytest tests/test_kml_parser.py -v
```
Les 12 tests doivent tous passer (dont celui sur votre vrai fichier).

---

Si `POST /map-layers/import` échoue à l'étape 1, c'est probablement soit
un souci de permissions (vérifiez que votre compte a `sites: write`), soit
un problème d'écriture dans `STORAGE_LOCAL_PATH` — copiez-moi l'erreur exacte.
