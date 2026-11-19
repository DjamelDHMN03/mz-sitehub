# Test manuel — Phase 15 (Partage documentaire)

## 1. Lancer les tests automatisés (déjà validés en local)

```bash
docker compose exec backend python -m pytest tests/test_share.py -v
```
Les 11 tests doivent passer.

## 2. Créer un lien de partage pour un document

```bash
DOC_ID="<id d'un document uploadé en Phase 11>"
curl -X POST http://localhost:8000/shares \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"document_ids\": [\"$DOC_ID\"], \"expiry_preset\": \"24h\"}"
```
Notez le `token` et le `share_url`, ainsi que `whatsapp_url`/`telegram_url`/
`outlook_compose_url`.

## 3. Consulter le lien SANS être connecté (simule le destinataire)

```bash
TOKEN_PARTAGE="<le token de l'étape 2>"
curl http://localhost:8000/shares/$TOKEN_PARTAGE/info
```
Doit fonctionner sans header Authorization, avec `"is_valid": true`.

## 4. Télécharger via le lien public

```bash
curl http://localhost:8000/shares/$TOKEN_PARTAGE/download -o /tmp/partage.pdf
```

## 5. Révoquer et vérifier que le téléchargement est bloqué

```bash
LINK_ID="<id du lien, renvoyé à l'étape 2>"
curl -X POST http://localhost:8000/shares/$LINK_ID/revoke -H "Authorization: Bearer $TOKEN"

curl -i http://localhost:8000/shares/$TOKEN_PARTAGE/download
```
Doit renvoyer `410 Gone`.

## 6. Partage multiple (ZIP)

```bash
DOC_ID_2="<id d'un deuxième document>"
curl -X POST http://localhost:8000/shares \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"document_ids\": [\"$DOC_ID\", \"$DOC_ID_2\"], \"expiry_preset\": \"7d\"}"
```
Téléchargez le lien obtenu : vous devez recevoir un `.zip` contenant les 2 fichiers.

## 7. Partager tout un dossier par catégorie (section 50)

```bash
SITE_ID="<id du site>"
curl -X POST http://localhost:8000/sites/$SITE_ID/share-folder \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"categories": ["APS", "CONTRATS"], "expiry_preset": "30d"}'
```

## 8. Interface web

- http://localhost:5173/documents → cliquer l'icône de partage sur un
  document → vérifier que le lien + les 3 boutons de plateforme apparaissent
- Ouvrir le `share_url` obtenu dans un onglet privé (pour simuler l'absence
  de session) → http://localhost:5173/share/{token} → vérifier l'affichage
  et le téléchargement

---

Dites-moi le résultat — j'enchaîne avec la Phase 16 (Import Excel) ensuite.
