# Test manuel — Phase 12 (Doc B / APS)

## 1. Créer un Doc B

```bash
SITE_ID="<id d'un site>"
curl -X POST http://localhost:8000/sites/$SITE_ID/doc-b \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"reference": "DOCB-2026-001", "organisme": "APC Reghaia", "status": "DEPOSE", "date_depot": "2026-08-01"}'
```

## 2. Créer un APS

```bash
curl -X POST http://localhost:8000/sites/$SITE_ID/aps \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"aps_type": "APS_V2", "observation": "Version corrigée après retour Radio Planning"}'
```

## 3. Type APS invalide (doit échouer)

```bash
curl -i -X POST http://localhost:8000/sites/$SITE_ID/aps \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"aps_type": "TYPE_INVENTE"}'
```
Doit renvoyer `400 Bad Request`.

## 4. Lier un document existant

Uploadez d'abord un document (Phase 11), puis :
```bash
DOC_ID="<id du document>"
curl -X PATCH http://localhost:8000/doc-b/<doc_b_id> \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"document_id\": \"$DOC_ID\"}"
```

## 5. Interface web

http://localhost:5173/doc-b (ou /aps, même page) → choisir le site → créer
un Doc B et un APS → vérifier qu'ils apparaissent dans leurs colonnes
respectives, avec le document lié si sélectionné.

---

Dites-moi le résultat — j'enchaîne avec la Phase 13 (Contrats) ensuite.
