# Test manuel — Phase 11 (Documents / GED)

## 1. Lancer les tests automatisés (déjà validés en local, à confirmer ici)

```bash
docker compose exec backend python -m pytest tests/test_storage.py tests/test_document_recognition.py -v
```
Les 9 tests doivent passer.

## 2. Upload avec détection automatique réussie

```bash
SITE_ID="<un id de site, ex. celui d'AL6328>"
echo "contenu de test" > /tmp/AL6328_APS_V2.pdf
curl -X POST "http://localhost:8000/sites/$SITE_ID/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/AL6328_APS_V2.pdf"
```
Doit renvoyer `"category": "APS"`, `"version": 2` — sans que vous ayez
précisé la catégorie.

## 3. Upload ambigu (nom générique)

```bash
echo "contenu" > /tmp/scan.pdf
curl -i -X POST "http://localhost:8000/sites/$SITE_ID/documents" \
  -H "Authorization: Bearer $TOKEN" -F "file=@/tmp/scan.pdf"
```
Doit renvoyer `422` avec le détail de l'ambiguïté et la liste des catégories valides.

Puis avec la catégorie explicite :
```bash
curl -X POST "http://localhost:8000/sites/$SITE_ID/documents?category=AUTRES" \
  -H "Authorization: Bearer $TOKEN" -F "file=@/tmp/scan.pdf"
```
Doit réussir.

## 4. Télécharger

```bash
DOC_ID="<id renvoyé à l'étape 2>"
curl http://localhost:8000/documents/$DOC_ID/download \
  -H "Authorization: Bearer $TOKEN" -o /tmp/telecharge.pdf
diff /tmp/AL6328_APS_V2.pdf /tmp/telecharge.pdf && echo "Contenu identique ✓"
```

## 5. Nouvelle version (ne doit jamais écraser silencieusement)

```bash
echo "contenu v3" > /tmp/AL6328_APS_V3.pdf
curl -X POST "http://localhost:8000/documents/$DOC_ID/new-version" \
  -H "Authorization: Bearer $TOKEN" -F "file=@/tmp/AL6328_APS_V3.pdf"
```
Doit renvoyer `"version": 3`. Vérifiez en base que l'ancienne version existe
toujours :
```bash
docker compose exec db psql -U mzsitehub -d mzsitehub \
  -c "SELECT version, storage_key FROM document_versions WHERE document_id='$DOC_ID';"
```

## 6. Interface web

http://localhost:5173/documents → choisir le site → glisser un fichier
`scan.pdf` (nom générique) → vérifiez que l'interface demande bien la
catégorie au lieu de deviner → confirmer → le document apparaît dans le tableau,
téléchargeable et supprimable.

---

Dites-moi le résultat — j'enchaîne avec la Phase 12 (Doc B / APS) ensuite.
