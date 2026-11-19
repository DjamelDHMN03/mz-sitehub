# Test manuel — Phase 8 (Carte)

## 1. Précondition
Avoir au moins un site avec GPS renseigné (voir étape 5 de
`docs/PHASE4_TEST_MANUEL.md` pour ajouter latitude/longitude à un site).

## 2. Lancer et ouvrir

```bash
docker compose up -d --build
```
Ouvrez http://localhost:5173/carte (menu **Carte**).

## 3. Ce que vous devez voir
1. Une carte OpenStreetMap centrée sur l'Algérie
2. Un point coloré à l'endroit du site que vous avez géolocalisé
3. Cliquer sur le point → popup avec code, statut, GPS, boutons
   "Google Maps" (ouvre un nouvel onglet) et "Copier"
4. Une légende à droite avec les couleurs réellement utilisées
5. Le filtre "Tous les statuts" doit lister les statuts existants

## 4. Point de vigilance le plus probable

Si l'installation `npm install` échoue sur `react-leaflet-cluster` ou si la
carte s'affiche en gris/blanc sans tuiles :
- Vérifiez que le CSS Leaflet est bien chargé (F12 → onglet Réseau →
  `leaflet.css` doit répondre 200)
- Copiez-moi l'erreur exacte de la console du navigateur ou du terminal
  `docker compose logs frontend` — c'est le point que je n'ai pas pu tester
  moi-même faute d'accès réseau ici.

## 5. Test avec plusieurs sites proches (clustering)

Créez 3-4 sites avec des coordonnées proches (à quelques centaines de mètres),
zoomez/dézoomez sur la carte : ils doivent se regrouper en une bulle avec un
chiffre, puis se séparer au zoom.

---

Dites-moi ce qui s'affiche (ou l'erreur) — je corrige avant la Phase 9.
