# Test manuel — Phase 6 (Dashboard)

## 1. Précondition
Avoir au moins 2-3 sites créés avec des statuts différents (voir
`docs/PHASE4_TEST_MANUEL.md`), pour voir les chiffres bouger.

## 2. Vérifier l'API directement

```bash
curl http://localhost:8000/dashboard/stats -H "Authorization: Bearer $TOKEN"
```

Vous devez voir un JSON avec `total_sites.value` égal au nombre de sites créés,
et les autres compteurs répartis selon leurs statuts. `a_relancer` et
`dossiers_incomplets` doivent avoir `"available": false`.

## 3. Vérifier dans le navigateur

Ouvrez http://localhost:5173, connectez-vous, la page d'accueil doit afficher
une grille de cartes avec ces chiffres. Les deux cartes non disponibles
doivent afficher "à venir" avec une petite note explicative — pas de "0"
qui laisserait croire à une vraie donnée.

## 4. Test de cohérence

Créez un nouveau site avec `status_id` correspondant au statut `BLOQUE`,
rafraîchissez le dashboard : le compteur "Bloqués" doit augmenter de 1 et
"Total sites" aussi.

---

Si les chiffres ne correspondent pas à ce que vous attendez, dites-moi
lesquels — la logique de regroupement des statuts est dans
`app/routers/dashboard.py` (`STATUS_GROUPS`) et peut être ajustée.
