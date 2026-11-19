# Test manuel — Phase 4 (Module Sites)

Prérequis : Phase 3 validée (vous avez un `TOKEN` d'accès valide, voir
`docs/PHASE3_TEST_MANUEL.md`).

## 1. Insérer les 58 wilayas et un statut par défaut si pas déjà fait

La migration crée déjà les statuts (`site_status`). Pour les wilayas, importez
votre référentiel officiel dans `wilayas`/`communes` (non fourni ici pour ne
pas inventer de données — section 74). Pour tester sans ça, un site peut être
créé avec `wilaya_id: null`.

## 2. Créer un site

```bash
curl -X POST http://localhost:8000/sites \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "code": "AL6328",
    "name": "EPIC EGUVA - Reghaia",
    "status_id": 1,
    "organisme": "EPIC EGUVA",
    "observation": "Accord de principe, DRH en négociation"
  }'
```
Doit renvoyer 201 avec le site créé, `latitude`/`longitude` à `null` (GPS inconnu).

## 3. Vérifier l'unicité du code

Relancez la même commande : doit renvoyer `409 Conflict`.

## 4. Lister et rechercher

```bash
curl "http://localhost:8000/sites?q=EGUVA" -H "Authorization: Bearer $TOKEN"
```

## 5. Modifier un champ (flexibilité totale — section 16)

```bash
SITE_ID="<coller l'id renvoyé à l'étape 2>"
curl -X PATCH http://localhost:8000/sites/$SITE_ID \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"latitude": 36.777, "longitude": 3.293}'
```
Relisez le site : `latitude`/`longitude` doivent être renseignées.

## 6. Changer le code (avec confirmation obligatoire)

```bash
curl -X PATCH http://localhost:8000/sites/$SITE_ID/code \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"new_code": "AL6328-BIS", "confirm": false}'
# -> 400 Bad Request (confirmation manquante)

curl -X PATCH http://localhost:8000/sites/$SITE_ID/code \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"new_code": "AL6328-BIS", "confirm": true}'
# -> 200, previous_codes contient maintenant "AL6328"
```

## 7. Corbeille

```bash
curl -X DELETE http://localhost:8000/sites/$SITE_ID -H "Authorization: Bearer $TOKEN"
# -> 204

curl http://localhost:8000/sites/trash -H "Authorization: Bearer $TOKEN"
# -> le site apparaît

curl -X POST http://localhost:8000/sites/$SITE_ID/restore -H "Authorization: Bearer $TOKEN"
# -> 200, le site redevient actif
```

## 8. Vérifier l'audit en base

```bash
docker compose exec db psql -U mzsitehub -d mzsitehub \
  -c "SELECT action, field, old_value, new_value, occurred_at FROM audit_logs ORDER BY occurred_at DESC LIMIT 10;"
```
Doit lister CREATE, UPDATE, CODE_CHANGE, DELETE, RESTORE dans l'ordre.

---

Si une étape échoue, copiez-collez l'erreur exacte — je corrige avant la Phase 5.
