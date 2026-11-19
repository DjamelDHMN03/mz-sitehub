# Test manuel — Phase 17 (Rapports / Exports)

Les fonctions de génération (CSV/Excel/PDF) sont déjà validées réellement —
voir `docs/screenshots/phase17_fiche_pdf_reelle.png` pour un aperçu concret
de la fiche PDF avec les vrais logos. Ce qui reste à valider ici, c'est le
routeur FastAPI qui les assemble avec les vraies données de votre base.

## 1. Export liste (Excel)

```bash
curl "http://localhost:8000/reports/sites/export?format=xlsx" \
  -H "Authorization: Bearer $TOKEN" -o /tmp/rapport_sites.xlsx
```
Ouvrez le fichier : vous devez voir tous vos sites actifs avec wilaya et
statut en toutes lettres (pas des ids).

## 2. Export liste filtrée (CSV)

```bash
curl "http://localhost:8000/reports/sites/export?format=csv&organisme=EGUVA" \
  -H "Authorization: Bearer $TOKEN" -o /tmp/rapport_eguva.csv
cat /tmp/rapport_eguva.csv
```
Doit contenir uniquement les sites dont l'organisme contient "EGUVA".

## 3. Fiche PDF d'un site réel

```bash
SITE_ID="<id d'un site avec au moins un contact>"
curl "http://localhost:8000/reports/sites/$SITE_ID/fiche-pdf" \
  -H "Authorization: Bearer $TOKEN" -o /tmp/fiche.pdf
```
Ouvrez le PDF : vérifiez que les logos MZ Building et Ooredoo apparaissent
bien (ça dépend du montage `./assets:/app/assets` dans docker-compose —
si absents, vérifiez `docker compose exec backend ls /app/assets/logos/`).

## 4. Export complet (ZIP)

```bash
curl "http://localhost:8000/reports/sites/$SITE_ID/export-complet" \
  -H "Authorization: Bearer $TOKEN" -o /tmp/export_complet.zip
unzip -l /tmp/export_complet.zip
```
Doit contenir tous les documents du site (rangés par catégorie) + un fichier
`{CODE}_FICHE.pdf`.

## 5. Interface web

http://localhost:5173/rapports → tester les 4 boutons d'export → vérifier
que chacun déclenche bien un téléchargement dans le navigateur.

---

Dites-moi le résultat — j'enchaîne avec la Phase 18 (Historique/Audit UI) ensuite.
