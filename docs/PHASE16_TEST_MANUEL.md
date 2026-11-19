# Test manuel — Phase 16 (Import Excel)

## 1. Lancer les tests automatisés (déjà validés en local avec un vrai .xlsx)

```bash
docker compose exec backend python -m pytest tests/test_excel_import.py -v
```
Les 6 tests doivent passer.

## 2. Préparer un fichier Excel de test

Créez un fichier `sites.xlsx` avec les colonnes : `Code Site`, `Nom du site`,
`Wilaya`, `Statut`. Mettez au moins une ligne avec un code déjà existant
dans votre base (pour tester UPDATE) et une ligne avec un nouveau code
(pour tester CREATE).

## 3. Prévisualiser

```bash
curl -X POST http://localhost:8000/import/excel/preview \
  -H "Authorization: Bearer $TOKEN" -F "file=@sites.xlsx"
```
Notez le `import_id` et vérifiez que `summary` reflète bien vos lignes
(CREATE/UPDATE/INCHANGE).

## 4. Confirmer

```bash
IMPORT_ID="<id renvoyé à l'étape 3>"
curl -X POST http://localhost:8000/import/excel/confirm \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"import_id\": \"$IMPORT_ID\"}"
```
Vérifiez `created`/`updated`, et regardez si des `warnings` apparaissent
(statut ou wilaya non reconnu — normal si vos wilayas ne sont pas encore
importées dans la table `wilayas`).

## 5. Test d'expiration du cache

Attendez... (ou modifiez temporairement `_CACHE_TTL_SECONDS` à 5 dans
`app/routers/excel_import.py` pour tester plus vite), puis appelez
`/import/excel/confirm` avec un `import_id` périmé : doit renvoyer `404`.

## 6. Interface web

http://localhost:5173/sites → bouton "Importer Excel" → glisser le fichier
→ vérifier le résumé et les badges par ligne → Confirmer → vérifier que
les sites créés/mis à jour apparaissent bien dans la liste des sites.

---

Dites-moi le résultat — j'enchaîne avec la Phase 17 (Rapports/Exports) ensuite.
