# Test manuel — Phase 3 (Authentification)

Comme l'environnement de construction n'a pas accès réseau pour installer les
paquets Python et lancer un test automatisé, voici comment valider vous-même
que l'authentification fonctionne, en 5 minutes.

## 1. Démarrer l'environnement

```bash
cp .env.example .env
docker compose up -d --build db backend
```

Vérifiez que l'API répond :
```bash
curl http://localhost:8000/health
# -> {"status":"ok","service":"mz-sitehub-backend"}
```

## 2. Créer le premier compte ADMIN

```bash
docker compose exec backend python -m scripts.seed_admin \
  --email admin@mzbuilding.dz \
  --password "changez-moi-immediatement" \
  --first-name Admin --last-name MZBuilding
```
Doit afficher : `✅ Compte ADMIN créé : admin@mzbuilding.dz`

## 3. Se connecter

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@mzbuilding.dz","password":"changez-moi-immediatement"}'
```
Doit renvoyer un JSON avec `access_token` et `refresh_token`.

## 4. Vérifier /auth/me avec le token

```bash
TOKEN="<coller le access_token ici>"
curl http://localhost:8000/auth/me -H "Authorization: Bearer $TOKEN"
```
Doit renvoyer votre profil avec `"role_code":"ADMIN"`.

## 5. Vérifier qu'un mauvais mot de passe est rejeté

```bash
curl -i -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@mzbuilding.dz","password":"faux"}'
```
Doit renvoyer `401 Unauthorized`.

## 6. Documentation interactive

Ouvrez http://localhost:8000/docs — tous les endpoints `/auth/*` doivent
apparaître avec leurs schémas.

---

Si une de ces étapes échoue, dites-moi exactement le message d'erreur — je
corrigerai avant de passer à la Phase 4.
