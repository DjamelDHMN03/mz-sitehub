# CARTOGRAPHY.md — MZ SITEHUB, Cartographie

## Technologie

Leaflet + OpenStreetMap — gratuit, aucune clé API, aucune limite d'usage
imposée par un fournisseur payant (section 20-22 du cahier des charges).

## Fonctionnement

- Chaque site avec un GPS renseigné apparaît automatiquement sur la carte
  (frontend/src/pages/CartePage.tsx)
- Couleur du marker = couleur réelle du statut en base (site_status.color,
  personnalisable par l'ADMIN, section 53) — jamais une couleur figée en dur
- Clustering automatique (react-leaflet-cluster) : les sites proches se
  regroupent en une bulle chiffrée, se séparent au zoom
- Clic sur un marker -> popup avec code, statut, GPS, lien Google Maps
  gratuit et bouton copier les coordonnées

## Import KMZ/KML

app/services/kml_parser.py — testé réellement contre un fichier fourni par
l'utilisateur (25 sites). Supporte Point, LineString, Polygon (avec trous),
MultiGeometry homogène. Détecte automatiquement :
- le code du site (dans le nom de l'objet ou du fichier)
- la catégorie probable si le nom suit une convention connue

Limite assumée : un Placemark contenant une géométrie hétérogène est
importé avec ses métadonnées (nom, description) mais sans géométrie
affichable sur la carte, plutôt que de générer une forme approximative.

## Rattachement automatique (section 29)

Après import, chaque objet avec un code détecté est comparé aux sites
existants :
- code trouvé -> proposition "Rattacher au site existant"
- code non trouvé -> proposition "Nouveau site détecté"

Rien n'est créé ou lié sans un clic explicite de l'utilisateur.

## Filtres et Assistant IA

L'Assistant IA peut transformer une phrase ("Affiche les sites de Blida",
"Masque les sites opérationnels") en filtre cartographique — voir
docs/AI.md. Limite assumée : le filtre actuel n'affiche qu'un seul statut
à la fois.

## Non construit dans cette version

- Outils de mesure de distance/surface sur la carte (section 104)
- Export KML/KMZ/GeoJSON depuis l'application (section 30)
- Recherche géographique par rayon (section 105)

Ces éléments sont des extensions naturelles de ce qui existe déjà (la
géométrie est en PostGIS, donc des requêtes de distance sont possibles
sans changement de schéma) mais n'ont pas été codés dans ces 25 phases.
