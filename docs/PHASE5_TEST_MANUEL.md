# Test manuel — Phase 5 (Frontend)

Comme pour les phases précédentes, pas d'accès réseau ici pour `npm install`
et lancer un vrai build/dev-server. Voici comment valider vous-même.

## 1. Lancer tout l'environnement

```bash
docker compose up -d --build
```

Ouvrez http://localhost:5173

## 2. Ce que vous devez voir

1. Redirection automatique vers `/login` (vous n'êtes pas connecté)
2. Le logo MZ Building, fond sombre (dark mode par défaut)
3. Connectez-vous avec le compte créé en Phase 3 (`scripts/seed_admin.py`)
4. Après connexion : sidebar avec les 16 entrées de menu, dashboard placeholder
5. Cliquez sur **Sites** : la liste doit se charger depuis l'API réelle
   (vide si vous n'avez pas encore créé de site — créez-en un via
   `docs/PHASE4_TEST_MANUEL.md` puis rafraîchissez)
6. Tapez dans la recherche : la liste doit se filtrer après ~300ms
7. Le badge de statut doit afficher un libellé et une couleur réels
   (pas juste "#1") — si vous voyez "#1", vérifiez que
   `GET http://localhost:8000/site-statuses` répond bien

## 3. Si `npm install` échoue ou le conteneur ne démarre pas

Dites-moi le message d'erreur exact (souvent une histoire de version Node
ou de cache npm) — je corrigerai `frontend/Dockerfile` ou `package.json`.

## 4. Vérification visuelle rapide de la palette

Les couleurs doivent être dérivées du dégradé du logo MZ Building : dominante
violet/magenta, jamais de noir pur en fond. Si ce n'est pas le cas,
`tokens.css` ne serait pas chargé — vérifiez que `global.css` est bien
importé dans `main.tsx`.

---

Dites-moi ce que vous observez (ou l'erreur exacte) — je corrige avant la Phase 6.
