# Test manuel — Phase 18 (Historique / Audit)

## 1. Vérifier que l'audit s'est déjà rempli depuis les phases précédentes

```bash
curl "http://localhost:8000/audit-logs?page_size=20" -H "Authorization: Bearer $TOKEN"
```
Vous devriez voir toutes les actions des tests précédents (CREATE/UPDATE/
DELETE sur sites, contacts, documents, contrats...).

## 2. Filtrer par entité

```bash
curl "http://localhost:8000/audit-logs?entity=sites" -H "Authorization: Bearer $TOKEN"
```

## 3. Filtrer par période

```bash
curl "http://localhost:8000/audit-logs?since=2026-09-01&until=2026-09-30" \
  -H "Authorization: Bearer $TOKEN"
```

## 4. Liste des entités tracées

```bash
curl http://localhost:8000/audit-logs/entities -H "Authorization: Bearer $TOKEN"
```
Doit lister au minimum : sites, contacts, documents, contracts, doc_b,
aps_documents, tasks, map_layers, document_share_links (selon ce que vous
avez testé jusqu'ici).

## 5. Interface web

http://localhost:5173/historique → vérifier que le tableau se remplit,
que le filtre par entité fonctionne, et que le diff (ancienne → nouvelle
valeur) est lisible pour une modification de statut de site par exemple.

---

Dites-moi le résultat — j'enchaîne avec la Phase 19 (Assistant IA) ensuite,
la plus attendue du projet.
