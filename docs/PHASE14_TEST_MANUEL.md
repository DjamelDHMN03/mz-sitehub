# Test manuel — Phase 14 (Actions / Kanban / Calendrier)

## 1. Créer une action

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title": "Relancer le DRH AL6328", "due_date": "2026-09-05", "priority": 1}'
```

## 2. Filtrer par plage de dates (utilisé par le calendrier)

```bash
curl "http://localhost:8000/tasks?due_after=2026-09-01&due_before=2026-09-30" \
  -H "Authorization: Bearer $TOKEN"
```

## 3. Marquer terminé

```bash
TASK_ID="<id renvoyé à l'étape 1>"
curl -X PATCH http://localhost:8000/tasks/$TASK_ID \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"status": "TERMINE"}'
```

## 4. Interface web

- http://localhost:5173/actions → créer l'action, cliquer sur le ✓ pour la marquer terminée
- http://localhost:5173/calendrier → vérifier qu'elle apparaît le 5 septembre 2026
- http://localhost:5173/sites → cliquer "Vue Kanban" → vérifier que les
  sites apparaissent dans la bonne colonne de statut, et que changer le
  sélecteur sur une carte déplace bien le site (rafraîchissez `/sites`
  ensuite pour confirmer que le statut a changé en base)

---

Dites-moi le résultat — j'enchaîne avec la Phase 15 (Partage documentaire) ensuite.
