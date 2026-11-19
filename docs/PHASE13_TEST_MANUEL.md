# Test manuel — Phase 13 (Contrats)

## 1. Créer un contrat sans montant connu

```bash
SITE_ID="<id d'un site, ex. AL6286 (Blida Mall, contrat envisagé 11 ans)>"
curl -X POST http://localhost:8000/sites/$SITE_ID/contracts \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"contract_type": "Bail commercial", "duration_years": 11, "status": "EN_PREPARATION"}'
```
Vérifiez que `amount` est bien `null` dans la réponse — pas `0`.

## 2. Ajouter les deux signataires

```bash
CONTRACT_ID="<id renvoyé>"
curl -X POST http://localhost:8000/contracts/$CONTRACT_ID/signatories \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"party": "OOREDOO", "name": "À COMPLÉTER", "role_label": "Représentant légal"}'

curl -X POST http://localhost:8000/contracts/$CONTRACT_ID/signatories \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"party": "PROPRIETAIRE", "name": "À COMPLÉTER"}'
```
Vérifiez que `has_signing_power` est `null` (pas `false`) sur les deux.

## 3. Contrats proches de l'expiration

```bash
curl "http://localhost:8000/contracts/expiring-soon?within_days=90" \
  -H "Authorization: Bearer $TOKEN"
```
Doit renvoyer une liste vide tant qu'aucun contrat n'a de `date_expiration`
dans les 90 prochains jours — testez en mettant à jour un contrat avec une
date d'expiration proche :
```bash
curl -X PATCH http://localhost:8000/contracts/$CONTRACT_ID \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"date_expiration": "2026-10-01"}'
```

## 4. Interface web

http://localhost:5173/contrats → choisir un site → créer un contrat →
vérifier que le montant affiche bien "À COMPLÉTER" en gris plutôt qu'un
chiffre → ajouter un signataire → vérifier le badge "Pouvoir à vérifier".

---

Dites-moi le résultat — j'enchaîne avec la Phase 14 (Actions/Kanban/Calendrier) ensuite.
