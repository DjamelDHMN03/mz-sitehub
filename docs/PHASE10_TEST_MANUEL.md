# Test manuel — Phase 10 (Contacts / CRM)

## 1. Vérifier le référentiel des fonctions

```bash
curl http://localhost:8000/contact-roles -H "Authorization: Bearer $TOKEN"
```
Doit lister les 19 fonctions (DG, DRH, PDG, Propriétaire, APC, OPGI...).

## 2. Créer un contact sur un site existant

```bash
SITE_ID="<un id de site créé en Phase 4>"
curl -X POST http://localhost:8000/sites/$SITE_ID/contacts \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"first_name": "Ameur", "last_name": "Benregreg", "role_label": "DRH", "phone": "0555000000"}'
```

## 3. Ajouter une interaction

```bash
CONTACT_ID="<id renvoyé à l'étape 2>"
curl -X POST http://localhost:8000/contacts/$CONTACT_ID/interactions \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"interaction_type": "APPEL", "summary": "Point sur le statut du DG", "next_action": "Relancer", "followup_at": "2026-09-15"}'
```

## 4. Vérifier la mise à jour automatique du contact

```bash
curl http://localhost:8000/sites/$SITE_ID/contacts -H "Authorization: Bearer $TOKEN"
```
`last_contact_at` doit être la date du jour, `next_followup_at` doit être `2026-09-15`.

## 5. Interface web

http://localhost:5173/contacts → choisir le site → voir/ajouter un contact
→ cliquer dessus → ajouter une interaction → vérifier qu'elle apparaît dans
l'historique et que la date de relance affichée en haut se met à jour.

## 6. Vérifier la permission ACQUISITION

Si vous avez un compte avec le rôle ACQUISITION (pas ADMIN), vérifiez qu'il
peut bien créer un contact — c'est le correctif de seed appliqué pendant
cette phase (voir `docs/ROADMAP.md`).

---

Dites-moi le résultat — j'attaque la Phase 11 (Documents/GED) ensuite.
