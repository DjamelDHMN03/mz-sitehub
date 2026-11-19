# Roadmap détaillée MZ SITEHUB

Reprend l'ordre de construction défini dans le cahier des charges (section 121),
avec pour chaque phase les livrables concrets attendus.

## Phase 1 — Architecture ✅
- Arborescence du monorepo
- docker-compose.yml, .env.example
- README.md

## Phase 2 — Base de données ✅
- `database/migrations/001_init_core_schema.sql` : 32 tables
  (users, roles, sites, site_history, contacts, contact_roles,
  contact_interactions, documents, document_versions, doc_b,
  aps_documents, contracts, contract_signatories, tasks, photos,
  site_status, wilayas, communes, notifications, audit_logs,
  map_layers, map_features, map_feature_sites, custom_fields,
  custom_field_values, document_share_links, document_share_history,
  document_share_recipients, ai_conversations, ai_messages,
  ai_document_chunks, ai_embeddings)
- Soft delete (`deleted_at`) sur toutes les tables métier
- PostGIS pour les géométries, pgvector pour le RAG

## Phase 3 — Authentification ✅
- Décision : JWT maison (validé avec l'utilisateur) plutôt que Supabase Auth
  → 0 DA, contrôle total du RBAC côté backend
- `app/core/security.py` : hash bcrypt (passlib) + création/validation JWT
  (access token 8h, refresh token 48h)
- `app/core/deps.py` : `get_current_user` + `require_permission(resource, level)`
  qui lit `roles.permissions` (JSON) et applique le RBAC — jamais côté frontend seul
- `app/routers/auth.py` : POST /auth/login, /auth/refresh, GET /auth/me,
  POST /auth/change-password
- `app/models/user.py` : ORM SQLAlchemy 2.0 mappé sur les tables `users`/`roles`
  de la migration 001 (aucune redéfinition de contrainte, la SQL reste source de vérité)
- `scripts/seed_admin.py` : création du premier compte ADMIN (jamais d'écrasement)
- Limite connue : pas d'accès réseau dans l'environnement de build pour installer
  les dépendances et lancer un test d'intégration réel ici — syntaxe et cohérence
  des imports vérifiées manuellement ; test réel à faire au premier `docker compose up`
  (voir `docs/PHASE3_TEST_MANUEL.md`)

## Phase 4 — Backend module Sites ✅
- `app/models/site.py` : ORM Wilaya/Commune/SiteStatus/Site/SiteHistory
  (géométrie PostGIS via GeoAlchemy2, mappé sur la migration 001)
- `app/models/audit.py` + `app/core/audit.py` : utilitaire d'audit générique
  réutilisable par tous les futurs modules (contacts, contrats, documents...)
- `app/schemas/site.py` : `SiteUpdate` avec TOUS les champs optionnels
  (flexibilité totale — section 16), lat/lon converties depuis/vers `geom`
- `app/routers/sites.py` :
  - `POST /sites`, `GET /sites` (filtres wilaya/statut/responsable/recherche
    texte + pagination), `GET /sites/{id}`, `PATCH /sites/{id}`
  - `PATCH /sites/{id}/code` : route dédiée avec `confirm=true` obligatoire,
    vérifie l'unicité, conserve l'ancien code dans `previous_codes` (section 17)
  - `DELETE /sites/{id}` (soft delete), `GET /sites/trash`,
    `POST /sites/{id}/restore`, `DELETE /sites/{id}/permanent` (ADMIN uniquement)
  - Chaque création/modification/suppression écrit une ligne d'audit
- Décision technique : le GPS n'est jamais inventé — `latitude`/`longitude`
  restent `null` tant que `geom` est `NULL` en base (section 74)
- Limite connue : toujours pas d'accès réseau ici pour un test d'intégration
  réel avec Postgres/PostGIS — voir `docs/PHASE4_TEST_MANUEL.md`

## Phase 5 — Frontend + Design System ✅
- Stack : React 18 + TypeScript strict + Vite + Tailwind, alias `@/` -> `src/`
- `tailwind.config.js` branché directement sur les CSS custom properties de
  `tokens.css` (Phase 1) — aucune couleur HEX dupliquée dans les composants
- Composants réutilisables construits (section 8) : `Button`, `Card`,
  `Badge`/`StatusBadge` (couleur dynamique lue depuis `site_status.color`,
  pas figée en dur), `Table`
- Layout : `Sidebar` avec les 16 entrées de navigation de la section 9,
  `Navbar`, `MainLayout` (redirige vers /login si non authentifié)
- `lib/api.ts` : client Axios avec refresh automatique du token à l'expiration
- `lib/auth.tsx` : contexte d'authentification (login/logout/persistance)
- Pages réellement branchées à l'API : `LoginPage` (POST /auth/login),
  `SitesPage` (GET /sites avec recherche debouncée + GET /site-statuses
  pour les vrais libellés/couleurs), `DashboardPage` (placeholder, Phase 6)
- Ajout backend minimal nécessaire : `GET /site-statuses` (lecture seule)
  pour ne pas afficher de fausses données de statut dans l'UI
- Décision : pas de pages vides pré-créées pour les 14 autres entrées du
  menu — elles arriveront au fil de leurs phases respectives
- Limite connue : pas d'accès réseau ici pour `npm install` / build réel —
  vérifié : JSON valides, tous les imports TS/TSX locaux et alias `@/`
  résolvent vers des fichiers existants ; voir `docs/PHASE5_TEST_MANUEL.md`

*(Phases 7 à 25 : voir README.md — chaque phase sera détaillée ici au fur et
à mesure de sa construction, avec les décisions techniques prises.)*

## Phase 6 — Dashboard ✅
- `app/models/tracking.py` : modèles minimaux Contract/DocB/ApsDocument
  (juste ce qu'il faut pour compter — complétés en Phase 12-13)
- `app/routers/dashboard.py` — `GET /dashboard/stats` : tous les indicateurs
  de la section 13, calculés par agrégation réelle (une requête groupée par
  code de statut + 2 requêtes ciblées pour contrats/Doc B)
- Décision assumée : "À relancer" et "Dossiers incomplets" nécessitent des
  modules pas encore construits (Contacts = Phase 10, Checklist = Phase 12+).
  Plutôt que d'inventer un calcul approximatif, l'API renvoie
  `available: false` + une note, et le frontend affiche "à venir" — cohérent
  avec la règle anti-invention (section 74/118) appliquée aux métriques
- `DashboardPage.tsx` : grille de cartes branchée sur `/dashboard/stats`,
  remplace le placeholder de la Phase 5
- Limite connue : toujours pas d'exécution réelle possible ici (pas de
  Postgres ni npm) — voir `docs/PHASE6_TEST_MANUEL.md`

## Phase 8 — Carte interactive ✅
- Leaflet + OpenStreetMap (`react-leaflet`), centrée sur l'Algérie par défaut
- Clustering via `react-leaflet-cluster` (+ `leaflet.markercluster`) — section 20
- Markers colorés dynamiquement via `L.divIcon` (pas d'image externe à gérer) :
  la couleur vient directement de `site_status.color` en base, donc reste
  cohérente avec les statuts personnalisables par l'ADMIN (section 53)
- `MapPopup` (composant réutilisable, section 8) : code, nom, statut, GPS,
  lien "Ouvrir dans Google Maps" (URL simple, gratuite — pas d'API payante,
  section 22) et bouton "Copier les coordonnées"
- Légende dynamique construite à partir des couleurs réellement utilisées
  par les statuts en base (pas une légende figée en dur)
- Filtre par statut ; les sites sans GPS sont explicitement comptés et
  exclus de la carte plutôt qu'affichés à une position inventée (section 74)
- Reporté à une phase ultérieure (sections 20/103-105, pas encore construit) :
  recherche sur la carte, plein écran natif, outils de mesure de
  distance/surface, import KMZ/KML (= Phase 9 dédiée)
- Limite connue : je ne peux toujours pas exécuter `npm install` ici pour
  vérifier que `react-leaflet-cluster` s'importe sans accroc avec les
  versions figées dans `package.json` — c'est le point le plus probable à
  surveiller au premier test réel (voir `docs/PHASE8_TEST_MANUEL.md`)

## Phase 9 — Import KMZ/KML/GeoJSON ✅
- **Testé réellement** (pas juste vérifié en syntaxe) contre le fichier fourni
  par l'utilisateur (`Coordonnees_GPS_STRATEGIC.kml`, 25 sites réels) —
  seule brique du projet exécutée de bout en bout jusqu'ici, car pur Python
  stdlib (`xml.etree`, `zipfile`), sans dépendance externe ni base de données
- **Bug réel trouvé et corrigé pendant la construction** : le regex de
  détection de code utilisait `\b`, qui ne coupe pas avant un `_` (considéré
  comme caractère de mot) — `AL6328_TSS.kmz` ne matchait pas. Corrigé avec
  des lookarounds explicites `(?<![A-Z0-9])...(?!\d)`. Test de non-régression
  ajouté (`test_detect_code_from_filename_with_underscore`)
- `app/services/kml_parser.py` : Point, LineString, Polygon (avec trous),
  MultiGeometry homogène (-> MultiPoint/MultiLineString/MultiPolygon) ;
  limitation assumée et documentée : MultiGeometry hétérogène (ex. Point +
  LineString dans le même Placemark) n'est pas convertie en géométrie
  PostGIS unique — la feature est quand même importée (nom, description,
  style, code) mais `geom = NULL`, plutôt que de générer un WKT inventé
- `app/services/geometry_wkt.py` : conversion GeoJSON -> WKT, testée sur
  les 25 vraies coordonnées du fichier fourni
- `backend/tests/test_kml_parser.py` : suite pytest permanente, y compris
  un test qui charge le vrai fichier utilisateur (copié dans
  `tests/fixtures/exemple_reel_25_sites.kml` — section 88)
- `app/routers/map_layers.py` : `POST /map-layers/import` (upload
  multipart), `GET /map-layers`, `PATCH` (renommer/afficher-masquer),
  `DELETE` (soft delete), `GET /{id}/features` (GeoJSON pour la carte),
  `GET /{id}/link-suggestions` + `POST /features/{id}/link` (section 29 :
  CRÉER/IGNORER/RATTACHER, avec confirmation utilisateur explicite avant
  toute création de site)
- `ImportCartePage.tsx` : drag & drop, résultats d'import, actions de
  rattachement en un clic (le site correspondant est déjà résolu côté
  backend par correspondance de code, pas de sélecteur manuel nécessaire)
- Reporté : export KML/KMZ/GeoJSON (section 30), lecture des styles
  référencés via `<styleUrl>` vers un `<Style>` global (seul le style
  inline est lu actuellement) — non couvert par le fichier de test fourni,
  donc non implémenté pour éviter du code jamais exécuté
- Limite connue : le routeur FastAPI lui-même (upload, DB, permissions)
  n'a pas pu être exécuté contre un vrai Postgres ici — seule la logique de
  parsing/conversion pure est réellement testée ; voir `docs/PHASE9_TEST_MANUEL.md`

## Phase 10 — Contacts / CRM ✅
- `app/models/contact.py` : ORM Contact/ContactRole/ContactInteraction
- `app/schemas/contact.py` : flexibilité totale sur `ContactUpdate` (même
  principe que Site), types d'interaction validés contre une liste fermée
  (section 34 : APPEL/WHATSAPP/EMAIL/REUNION/VISITE/COURRIER/AUTRE)
- `app/routers/contacts.py` :
  - `GET /contact-roles` (référentiel des 19 fonctions de la section 32)
  - `POST/GET /sites/{site_id}/contacts`, `PATCH/DELETE /contacts/{id}`
  - `POST/GET /contacts/{id}/interactions` — chaque nouvelle interaction
    met automatiquement à jour `last_contact_at`/`next_followup_at` sur la
    fiche contact (pas de double-saisie)
- **Correction de seed découverte pendant la construction** : les
  permissions du rôle MANAGER (migration 001) ne couvraient pas la
  ressource `contacts` — corrigé directement dans la migration (le projet
  n'a pas encore été déployé nulle part, donc pas de risque de casser une
  base existante) ; le routeur exige `contacts: write_own` plutôt que
  `write` pour que le rôle ACQUISITION (section 11) y ait accès
- `ContactsPage.tsx` : sélection d'un site → liste de ses contacts → fiche
  + historique d'interactions, ajout de contact et d'interaction en ligne
- Reporté : fiche site à onglets unifiée (Phase 7 différée) — pour l'instant
  Contacts est une page autonome avec un sélecteur de site, en attendant
- Limite connue : non exécuté contre une vraie base (comme les phases
  backend précédentes hors Phase 9) ; voir `docs/PHASE10_TEST_MANUEL.md`

## Phase 11 — Documents / GED ✅
- `app/services/storage.py` : abstraction `StorageProvider` (local aujourd'hui,
  squelette Supabase prêt sans implémentation tant qu'aucune clé n'est
  fournie — section 68). **Testée réellement** : sauvegarde/lecture/suppression
  + protection anti path-traversal vérifiée
- `app/services/document_recognition.py` : reconnaissance code/catégorie/version
  depuis le nom de fichier (section 41). **Testée réellement**, y compris
  l'exemple exact du cahier des charges (`AL6328_APS_V2.pdf` -> AL6328/APS/V2)
  et les cas ambigus (aucune fausse détection forcée — section 41 : "Si
  ambigu, demander confirmation")
- `backend/tests/test_storage.py` + `test_document_recognition.py` : suites
  pytest permanentes reprenant tous ces cas
- `app/routers/documents.py` : upload avec limite de taille (50 Mo),
  téléchargement toujours via route authentifiée (jamais d'URL de stockage
  brute — section 51), nouvelle version qui archive l'ancienne au lieu
  d'écraser (section 42), suppression = soft delete uniquement
- `DocumentsPage.tsx` : upload drag & drop, **gestion réelle de l'ambiguïté**
  (si la catégorie n'est pas détectée, l'utilisateur est invité à la choisir
  plutôt que de laisser le système deviner), téléchargement, suppression
- Reporté : partage (Outlook/WhatsApp/Telegram/liens sécurisés — sections
  44-51), lecture des Doc B/APS/Contrats comme entités dédiées au-delà du
  document générique (Phase 12-13)
- Limite connue : le routeur FastAPI (upload multipart, DB) non exécuté
  contre un vrai serveur ici ; seules les briques services (storage,
  reconnaissance) sont réellement testées — voir `docs/PHASE11_TEST_MANUEL.md`

## Phase 12 — Doc B / APS ✅
- `app/models/tracking.py` : `DocB`/`ApsDocument` complétés avec tous les
  champs des sections 37-38 (même classes/table qu'en Phase 6 — pas de
  nouveau modèle dupliqué, SQLAlchemy interdit deux classes sur une même
  table dans le même registre)
- Décision assumée : ni `doc_b` ni `aps_documents` n'ont de colonne
  `deleted_at` dans la migration 001 — suppression réelle (pas de soft
  delete) pour ces deux tables ; le Document sous-jacent (fichier + ses
  versions, Phase 11) n'est jamais touché par cette suppression
- `app/routers/docb_aps.py` : CRUD complet pour Doc B et APS, chaque
  enregistrement peut être lié à un `document_id` déjà uploadé (pas de
  duplication de la gestion de fichier — réutilise la GED de la Phase 11)
- Types APS validés contre la liste fermée de la section 38 (APS_V1/V2/V3,
  PLAN_GC, PLAN_STRUCTURE, PLAN_TOITURE, PLAN_PYLONE, PLAN_RADIO, TSS,
  PHOTO_TECHNIQUE)
- `DocBApsPage.tsx` : deux panneaux côte à côte par site, chacun avec
  formulaire de création et sélection d'un document déjà uploadé ; les
  entrées "Doc B" et "APS / Plans" du menu pointent vers cette même page
  pour l'instant (elle couvre les deux sections)
- Limite connue : non exécuté contre un vrai Postgres ici, comme les
  modules backend hors Phase 9/11 ; voir `docs/PHASE12_TEST_MANUEL.md`

## Phase 13 — Contrats ✅
- `app/models/tracking.py` : `Contract` complété avec tous les champs de la
  section 35 (référence, type, durée, dates, montant, périodicité, révision,
  conditions...) ; nouveau modèle `ContractSignatory` (section 36)
- Règle appliquée strictement (section 74/118) : aucun montant, date, ou
  statut de pouvoir de signature n'a de valeur par défaut inventée —
  `has_signing_power` reste `null` ("à vérifier") tant que non confirmé
  explicitement, jamais `false` par défaut qui laisserait croire à une
  vérification déjà faite
- `app/routers/contracts.py` : CRUD contrats + signataires, soft delete,
  audit ; `GET /contracts/expiring-soon` (section 72/96 : contrats proches
  de l'expiration — brique posée pour l'Assistant IA et les Rapports)
- `ContractsPage.tsx` : sélection site → liste contrats → détail avec
  montant explicitement marqué "À COMPLÉTER" si absent (jamais un "0" qui
  pourrait passer pour une vraie valeur), gestion des signataires avec
  badge "Pouvoir à vérifier" distinct de "Pouvoir vérifié"
- Limite connue : non exécuté contre un vrai Postgres ici ; voir
  `docs/PHASE13_TEST_MANUEL.md`

## Phase 14 — Actions / Kanban / Calendrier ✅
- `app/models/task.py` + `app/routers/tasks.py` : CRUD complet des tâches
  (section 54), `site_id` optionnel (une action peut être générale, fidèle
  à la migration 001 qui ne met pas cette colonne en NOT NULL)
- `ActionsPage.tsx` : liste filtrable par statut, marquage rapide "terminé",
  mise en évidence des échéances dépassées
- `CalendrierPage.tsx` : vue mensuelle construite à partir de `GET /tasks`
  filtré par plage de dates (section 55) — aucune nouvelle route backend,
  réutilisation directe de l'API Tasks
- `KanbanPage.tsx` : pipeline des SITES par statut (section 56 — à ne pas
  confondre avec le statut des tâches). Décision : pas de librairie de
  drag & drop ajoutée pour cette V1 (poids/risque supplémentaire non
  justifié) — le déplacement se fait via un sélecteur sur chaque carte,
  qui appelle simplement `PATCH /sites/{id}` déjà construit en Phase 4.
  Colonnes = statuts réels de la base, donc déjà "configurables" au sens
  de la section 53 (ADMIN peut modifier `site_status`)
- Décision de navigation : la section 9 ne liste pas "Kanban" comme entrée
  de sidebar séparée — accessible via un bouton "Vue Kanban" depuis la
  page Sites plutôt que d'ajouter une entrée non prévue au menu
- Limite connue : non exécuté contre un vrai Postgres ici ; voir
  `docs/PHASE14_TEST_MANUEL.md`

## Phase 15 — Partage documentaire ✅
- `app/services/share.py` : génération de token opaque (32 octets
  d'entropie), calcul d'expiration (24h/7j/30j/personnalisé — section 47),
  empaquetage ZIP en mémoire pour le partage multiple (section 49).
  **Testé réellement** : unicité des tokens, bornes d'expiration, détection
  lien expiré/révoqué, ZIP avec gestion des doublons de nom sans écrasement
- `backend/tests/test_share.py` : suite pytest permanente de ces cas
- `app/models/share.py` + `app/schemas/share.py` (déjà préparés avant cette
  session de construction, vérifiés et complétés)
- `app/routers/share.py` :
  - `POST /shares` (partage de documents précis), `POST /sites/{id}/share-folder`
    (section 50 : partager des catégories entières en un clic)
  - `POST /shares/{id}/revoke`, `GET /sites/{id}/shares` (historique, section 48)
  - Endpoints **publics** (sans authentification, car le destinataire n'a pas
    de compte) : `GET /shares/{token}/info` et `GET /shares/{token}/download`
    — revérifient l'expiration/révocation à CHAQUE accès, jamais une seule
    fois à la création (section 47 : un lien qui expire doit vraiment arrêter
    de fonctionner)
  - Le fichier ne transite jamais par une URL de storage brute — toujours
    via le token, conformément à la section 51
- Liens Outlook/WhatsApp/Telegram : ce sont des **deep links de composition**
  (mailto/wa.me/t.me pré-remplis), jamais un envoi automatique — l'utilisateur
  voit la fenêtre s'ouvrir et doit cliquer lui-même sur Envoyer (section 44)
- `SharePage.tsx` : route publique `/share/:token`, en dehors de `MainLayout`
  (pas de connexion requise) — affiche les fichiers et un bouton de
  téléchargement, ou un message clair si le lien est expiré/révoqué
- `DocumentsPage.tsx` : bouton de partage par document, affiche le lien +
  les 3 boutons de plateforme + copier
- Reporté : sélection multiple de documents dans l'UI pour un partage groupé
  (l'API le supporte déjà via `document_ids: [...]`, il manque juste la
  sélection multiple côté tableau) ; interface de "Partager le dossier"
  (l'API existe, pas encore de bouton dédié dans DocBApsPage/DocumentsPage)
- Limite connue : non exécuté contre un vrai Postgres/serveur ici ; seule la
  brique service (token/expiration/ZIP) est réellement testée — voir
  `docs/PHASE15_TEST_MANUEL.md`

## Phase 16 — Import Excel ✅
- `app/services/excel_import.py` : détection automatique de colonnes
  (tolère accents/casse/variations de libellés), comparaison avec les
  sites existants par code. **Testé réellement avec un vrai fichier .xlsx**
  généré via openpyxl (déjà disponible dans cet environnement, contrairement
  aux dépendances FastAPI) — lignes vides ignorées sans erreur, colonne
  Code manquante détectée, ligne sans code jamais transformée en site
  fantôme (`IGNORE_NO_CODE`)
- `backend/tests/test_excel_import.py` : suite pytest permanente de ces cas
- `app/routers/excel_import.py` : flux en 2 temps fidèle à la section 60
  ("afficher les différences avant validation") — `POST /import/excel/preview`
  ne touche jamais la base, `POST /import/excel/confirm` applique
  seulement après validation explicite
- Règle anti-invention appliquée à la synchronisation : si un statut ou une
  wilaya du fichier Excel ne correspond à aucune valeur existante en base,
  la ligne est signalée en avertissement plutôt que rattachée à une valeur
  approximative ; une création sans statut résolu est refusée plutôt que
  de forcer un statut par défaut
- Limite assumée : la prévisualisation est gardée en mémoire du process
  (30 min), pas dans une file partagée — suffisant pour un déploiement V1
  mono-instance (0 DA), à revoir seulement si le projet passe en multi-instance
- `ImportExcelPage.tsx` : glisser-déposer, résumé CREATE/UPDATE/INCHANGE,
  confirmation explicite avant écriture ; accessible depuis Sites (comme
  Kanban, "Import Excel" n'est pas une entrée de sidebar séparée dans la
  section 9)
- Limite connue : le routeur FastAPI (upload, DB) non exécuté contre un
  vrai serveur ici, comme les modules hors Phase 9/11/15/16 ; voir
  `docs/PHASE16_TEST_MANUEL.md`

## Phase 17 — Rapports / Exports ✅
- `app/services/export.py` : CSV (stdlib `csv`), Excel (`openpyxl`), PDF
  (`reportlab`) — **les trois testés réellement**, y compris un vrai PDF
  généré avec les logos MZ Building/Ooredoo fournis, converti en image et
  inspecté visuellement (voir `docs/screenshots/phase17_fiche_pdf_reelle.png`)
- Vérifié à l'œil : la fiche PDF respecte la règle anti-invention — les
  champs absents (adresse, GPS, téléphone du contact) affichent
  "À COMPLÉTER" plutôt qu'un blanc silencieux ou une valeur estimée
- `backend/tests/test_export.py` : suite pytest permanente (4 tests, tous
  exécutés manuellement avec succès faute de pytest installé ici)
- `app/routers/reports.py` :
  - `GET /reports/sites/export` (xlsx/csv, filtres wilaya/statut/organisme/date)
  - `GET /reports/sites/{id}/fiche-pdf` (section 78, logos inclus)
  - `GET /reports/sites/{id}/export-complet` (section 79 : ZIP de tous les
    documents du site + la fiche PDF récapitulative — réutilise
    `build_zip_archive` de la Phase 15, pas de nouvelle logique ZIP)
- Un document manquant sur le disque (jamais censé arriver, mais possible en
  cas d'incident) ne fait pas échouer tout l'export complet — il est
  simplement absent du ZIP plutôt que de bloquer les autres fichiers
- `docker-compose.yml` : ajout du montage `./assets:/app/assets` (sinon les
  logos ne seraient trouvés qu'en environnement de build, pas à l'exécution)
- `RapportsPage.tsx` : export liste filtrée, fiche PDF et export complet
  par site, chacun déclenchant un vrai téléchargement de fichier
- Reporté : génération de rapport par IA en langage naturel (section 96,
  nécessite l'Assistant IA — Phase 19)
- Limite connue : le routeur FastAPI (assemblage des requêtes DB) non
  exécuté contre un vrai serveur ici — seules les fonctions de génération
  pure (export.py) sont réellement testées ; voir `docs/PHASE17_TEST_MANUEL.md`

## Phase 18 — Historique / Audit (interface) ✅
- Pas de nouvelle brique de traçage : réutilise `audit_logs` alimenté par
  `log_audit()` depuis la Phase 4 dans TOUS les modules construits depuis
  (sites, contacts, documents, contrats, tâches, partage, import Excel...)
- `app/routers/audit.py` : `GET /audit-logs` (filtres entité/entity_id/
  utilisateur/action/période, pagination), `GET /audit-logs/entities`
  (liste dynamique des entités réellement tracées — évite une liste figée
  en dur qui pourrait diverger de ce qui existe vraiment en base)
- Lecture seule stricte : aucune route de modification/suppression de
  l'audit n'existe, conformément à sa fonction de traçabilité
- `HistoriquePage.tsx` : tableau chronologique avec filtre par entité,
  badges colorés par type d'action, diff ancienne→nouvelle valeur affiché
  inline
- Limite connue : non exécuté contre un vrai Postgres ici, comme la
  majorité des routeurs hors Phase 9/11/15/16/17 ; voir
  `docs/PHASE18_TEST_MANUEL.md`

## Phase 19 — Assistant IA ✅
- `app/ai/provider.py` : couche `AIProvider` (section 67) — `OllamaProvider`
  (implémentation HTTP suivant l'API officielle Ollama `/api/chat` et
  `/api/embeddings`), `AnthropicProvider` en squelette non implémenté tant
  qu'aucune clé n'est fournie (section 68). **Non exécutable ici** (pas
  d'Ollama qui tourne dans cet environnement de construction) — c'est la
  limite assumée de cette phase, voir plus bas
- `app/ai/intent.py` : analyseur d'intention déterministe, **testé
  réellement contre les 12 exemples exacts du cahier des charges**
  (sections 62, 63, 69 — y compris "Ajoute BENREGREG AMEUR comme DRH de
  AL6328.") + cas limites (phrases hors périmètre -> jamais de faux
  positif). Décision technique clé : ce moteur à règles fonctionne SANS
  aucun LLM, donc l'Assistant répond déjà utilement à 0 DA même si Ollama
  n'est jamais configuré — le LLM (quand branché) ne ferait qu'élargir la
  couverture aux formulations non reconnues, sans remplacer cette base
- `app/ai/tools.py` : les fonctions qui vont réellement chercher la donnée
  en base (sites par statut/wilaya, sites sans GPS, sites sans APS, résumé
  site, documents manquants, contrats expirants, recherche de contact par
  fonction). Le LLM ou l'analyseur d'intention ne fait QUE choisir quel
  tool appeler — jamais répondre depuis sa propre "mémoire"
- `app/ai/assistant.py` : orchestrateur reliant intention -> tool -> réponse
  formatée. **Testé réellement avec les tools mockés** (logique de
  branchement, formatage, gestion des listes vides, structuration du filtre
  carte) — seule la couche DB elle-même n'est pas exécutée ici
- Anti-hallucination (section 66) : `NOT_AVAILABLE_MESSAGE` = exactement
  "Information non disponible dans MZ SITEHUB." renvoyé verbatim quand un
  site/contact n'existe pas, jamais une réponse approximative
- Confirmation d'action (section 69) : `POST /assistant/chat` détecte une
  action ("Ajoute X comme Y de Z") et renvoie un `pending_action` — **rien
  n'est écrit en base tant que** `POST /assistant/confirm-action` n'est pas
  appelé explicitement (clic sur CONFIRMER côté frontend)
- IA + carte (section 63) : "Affiche/Masque les sites..." renvoie un filtre
  structuré, pas du texte ; le frontend propose un bouton "Voir sur la
  carte" qui navigue vers `/carte?status=...` — `CartePage` lit ce paramètre
  au chargement. Limitation assumée : le filtre carte actuel est un
  "afficher uniquement ce statut" (dropdown simple), donc un "masquer"
  se traduit pour l'instant par la même mécanique inversée manuellement —
  un vrai filtre d'exclusion multi-statuts serait nécessaire pour une
  sémantique parfaite de "masquer" (amélioration future, section 103)
- `AssistantPage.tsx` : chat avec historique, suggestions rapides
  (section 111), boutons Confirmer/Annuler sur les actions, lien direct
  vers la carte filtrée
- Reporté à la Phase 20 (RAG) : analyse de documents PDF, génération
  d'email (section 70), citation de sources documentaires
- **Limite majeure et assumée de cette phase** : sans Ollama démarré, le
  cœur "compréhension du langage naturel libre" n'a pas pu être testé à
  l'exécution — seule la mécanique déterministe (intent.py) l'a été,
  intégralement. Le jour où Ollama tournera, il faudra valider concrètement
  `OllamaProvider.chat()` contre le vrai serveur (aucune garantie que le
  format de function-calling attendu correspond exactement à ce que le
  modèle 8B choisi produit — à ajuster à ce moment-là). Voir
  `docs/PHASE19_TEST_MANUEL.md`

## Phase 20 — RAG ✅
- `app/services/rag.py` : extraction texte PDF page par page (`pypdf`),
  chunking avec chevauchement, similarité cosinus, classement par
  pertinence. **Testé réellement**, y compris l'extraction sur un vrai PDF
  (celui généré en Phase 17), un PDF généré à la volée via reportlab dans
  le test lui-même, une page vide (scan non-OCRisé) qui ne plante rien, un
  PDF invalide qui lève une erreur claire, et un classement de pertinence
  vérifié avec des vecteurs de test
- `backend/tests/test_rag.py` : suite pytest permanente (6 tests, rejoués
  manuellement avec succès faute de pytest installé ici)
- `app/models/ai_rag.py` : `AIDocumentChunk`/`AIEmbedding` sur pgvector
  (dimension 768, calée sur `nomic-embed-text` — à ajuster si un autre
  modèle d'embedding est configuré)
- `app/routers/rag.py` :
  - `POST /rag/documents/{id}/index` : PDF -> pages -> chunks -> embeddings
    (via `AIProvider.embed()`, donc **nécessite Ollama démarré** — échoue
    explicitement sinon, jamais de vecteur inventé)
  - `POST /rag/search` : recherche sémantique via l'opérateur pgvector
    `<=>` directement en SQL (performant même à l'échelle, section 84),
    renvoie TOUJOURS la source (nom de fichier + numéro de page) avec
    chaque résultat — jamais une réponse sans citation (section 65)
- `AssistantPage.tsx` : mode "Rechercher dans les documents" avec affichage
  systématique de la source et du score de pertinence ; message clair si
  Ollama n'est pas démarré plutôt qu'une erreur technique brute
- `DocumentsPage.tsx` : bouton d'indexation par document PDF
- **Limite majeure et assumée** (comme la Phase 19) : le pipeline complet
  extraction->chunking->embeddings->recherche n'a pu être testé de bout en
  bout qu'à moitié — tout ce qui précède l'appel à Ollama (extraction,
  chunking, classement) est réellement validé ; l'appel réseau à
  `/api/embeddings` et la requête pgvector elle-même ne le sont pas. Le
  jour où Ollama tourne, indexez un vrai document et lancez une recherche
  test — voir `docs/PHASE20_TEST_MANUEL.md`
- Reporté : génération d'email par IA (section 70), analyse comparative de
  documents ("Compare V1 et V2" — section 64), génération de rapport en
  langage naturel (section 96) — nécessitent le LLM conversationnel
  complet, pas seulement les embeddings

## Phase 21 — Sécurité ✅
- **Audit réel du code existant** plutôt que de réimplémenter ce qui l'était
  déjà — voir `docs/SECURITY.md` pour la synthèse complète
- Trois vrais trous trouvés et corrigés :
  1. `map_layers.py` et `excel_import.py` n'avaient AUCUNE limite de taille
     d'upload (seul `documents.py` en avait une) — centralisé dans
     `app/core/upload_limits.py`, testé réellement
  2. Aucune protection contre le bourrage de mot de passe sur `/auth/login`
     — `app/core/rate_limit.py` (fenêtre glissante, 5 échecs/5min),
     **testé réellement y compris l'expiration temporelle** (avec un vrai
     `time.sleep`)
  3. CORS figé en dur sur `localhost:5173` dans le code, non configurable
     pour un vrai déploiement — déplacé vers `.env` (`CORS_ALLOWED_ORIGINS`)
- Ajouts complémentaires : longueur minimale de mot de passe (8 caractères),
  en-têtes de sécurité HTTP de base, avertissement au démarrage si le
  secret JWT par défaut n'a pas été changé
- `backend/tests/test_rate_limit.py` : suite pytest permanente (6 tests,
  déjà exécutés avec succès ci-dessus)
- Documenté explicitement ce qui reste à la charge du déploiement (HTTPS
  via reverse proxy, isolation réseau de la base) plutôt que de prétendre
  le couvrir dans le code applicatif
- Limite connue : audit de code, pas un test d'intrusion réel

## Phase 22 — Tests ✅
- `backend/tests/conftest.py` : configuration pytest centralisée
- `backend/pyproject.toml` : config pytest (markers `integration`/`requires_ollama`
  pour distinguer clairement ce qui nécessite Docker/Ollama de ce qui ne
  le nécessite pas)
- **Consolidation réelle** : les 9 fichiers de test accumulés depuis la
  Phase 9 ont été exécutés ENSEMBLE pour la première fois (jusqu'ici,
  chacun avait été testé isolément au moment de sa création). Comme le
  vrai `pytest` n'est pas installable ici (pas d'accès réseau), un shim
  minimal ponctuel (`pytest.raises`, `pytest.mark.skipif`, stub
  `pydantic_settings`) a permis de lancer la suite complète — **65/65 tests
  passent**. Ce shim n'est pas livré dans le projet ; `docs/TESTING.md`
  explique précisément la méthode et donne le tableau de couverture complet
- Aucun nouveau bug trouvé pendant cette consolidation (contrairement aux
  Phases 9/16/21 qui en avaient révélé) — bon signe que les phases
  précédentes n'interfèrent pas entre elles
- `docs/TESTING.md` documente honnêtement la limite structurelle : cette
  suite couvre la logique pure, pas les endpoints FastAPI contre une vraie
  base, ni le frontend (aucun test Vitest/Playwright écrit)

## Phase 23 — Optimisation ✅
- **Audit réel** de l'existant plutôt que d'ajouter des optimisations non
  justifiées : la Phase 2 avait déjà GIST sur les géométries, GIN trigram
  sur `sites.code`, ivfflat sur les embeddings — bonne base
- **Vrai trou trouvé** : aucune clé étrangère n'avait d'index (contacts,
  documents, contrats, tâches, couches carto, partage, RAG...) —
  PostgreSQL n'indexe jamais les FK automatiquement. À l'échelle visée par
  la section 84 (10 000 sites / 100 000 documents), chaque
  `WHERE site_id = X` aurait fait un scan complet de table
- `database/migrations/002_add_missing_indexes.sql` : 25 index ajoutés,
  **migration additive** (ne modifie jamais la 001 — bonne pratique
  migratoire) ; chaque index vérifié programmatiquement contre les vraies
  colonnes déclarées en migration 001 (script de vérification exécuté,
  aucune erreur)
- **Vrai trou trouvé** : `GET /tasks` n'avait aucune pagination — corrigé
  avec le même pattern que `/sites`/`/audit-logs` (page/page_size, max 200) ;
  `ActionsPage.tsx` et `CalendrierPage.tsx` mis à jour pour le nouveau
  format de réponse
- Cache HTTP léger sur les référentiels quasi statiques (`/site-statuses`,
  `/contact-roles`) — évite un aller-retour DB à chaque écran affichant un
  badge, sans risque de donnée périmée grave (60s/300s, `private`)
- Déjà en place depuis les phases précédentes et non dupliqué ici :
  clustering carte (Phase 8), pagination sites (Phase 4), cache en mémoire
  du preview Excel (Phase 16) — décision de ne pas ajouter de Redis pour
  cette V1 (0 DA, complexité non justifiée à ce stade)
- Limite connue : aucun `EXPLAIN ANALYZE` réel possible sans Postgres
  démarré — les index sont corrects structurellement mais leur impact
  réel sur les plans de requête n'a pas pu être mesuré ici

## Phase 24 — Déploiement gratuit ✅
- **Recherche web des limites actuelles avant de documenter** (conformément
  à la consigne du cahier des charges section 91 : "vérifier les limites
  réelles au moment du déploiement") plutôt que de se fier à des
  connaissances possiblement datées :
  - Cloudflare Pages : bande passante illimitée, 500 builds/mois — confirmé
  - Supabase Free : PostGIS **et** pgvector inclus nativement, mais projet
    **mis en pause après 7 jours d'inactivité** — point de vigilance réel
  - Render Free : **512 Mo de RAM**, mise en veille après 15 min
    d'inactivité, **stockage disque éphémère** — ce dernier point est un
    vrai problème pour `STORAGE_DRIVER=local` (Phase 11) en production,
    documenté avec sa solution (implémenter enfin `SupabaseStorageProvider`,
    dont le squelette attendait depuis la Phase 11)
- `render.yaml` : blueprint prêt à l'emploi pour le backend
- `docs/DEPLOYMENT.md` : guide complet en 5 étapes (Supabase -> Render ->
  Cloudflare Pages -> Ollama sur machine propre -> keep-alive optionnel),
  avec chaque point de vigilance découvert explicitement signalé plutôt que
  dissimulé
- `.github/workflows/keep-alive.yml` : ping périodique gratuit (GitHub
  Actions) pour limiter les mises en veille — désactivé proprement tant
  que l'URL réelle n'est pas configurée, pour ne pas faire échouer le
  dépôt avant un premier déploiement
- **Rien de ce document n'a pu être testé par un déploiement réel** — c'est
  la limite la plus franche de tout le projet : aucun compte sur ces
  services n'existe dans cet environnement de construction. Le premier
  vrai déploiement révélera sûrement des ajustements

## Phase 25 — Documentation ✅ (dernière phase)
- Tous les documents listés en section 93 du cahier des charges créés :
  `INSTALLATION.md`, `USER_GUIDE.md` (section 94, style pas-à-pas simple
  pour non-techniciens), `ADMIN_GUIDE.md`, `ARCHITECTURE.md`, `AI.md`,
  `CARTOGRAPHY.md`, `BACKUP.md` — en plus de `SECURITY.md` (Phase 21),
  `DEPLOYMENT.md` (Phase 24) et `TESTING.md` (Phase 22) déjà écrits
- `README.md` réécrit comme point d'entrée unique : les 25 phases toutes
  cochées, un tableau de navigation vers chaque document, ET une section
  "Limites connues, honnêtement" qui résume la frontière entre ce qui a
  été réellement testé pendant la construction (65 tests, plusieurs bugs
  trouvés et corrigés) et ce qui reste cohérent statiquement mais jamais
  exécuté contre un vrai Postgres/Ollama/npm — pour que la première
  personne qui ouvre ce dépôt sache exactement où porter son attention
- Décision : ne pas gonfler la documentation avec des sections aspirantes
  sur des fonctionnalités non construites — chaque guide décrit ce qui
  existe réellement, avec les manques explicitement signalés (ex.
  ADMIN_GUIDE.md dit clairement que l'écran Utilisateurs n'a pas
  d'interface web et donne la commande SQL/CLI de contournement)

---

# Bilan des 25 phases

MZ SITEHUB est allé aussi loin qu'il est raisonnablement possible d'aller
en une seule session de construction assistée, avec les moyens réels de
cet environnement (pas de Postgres, pas d'Ollama, pas de npm install
possible). Trois catégories de résultats :

1. **Réellement testé et vérifié** (Phases 9, 11, 15, 16, 17, 19 partiel,
   20 partiel, 21, 22, 23) : parsing KML sur un vrai fichier fourni (bug
   trouvé et corrigé), reconnaissance de documents, import Excel sur un
   vrai .xlsx, génération PDF avec les vrais logos, tokens de partage,
   chunking RAG sur un vrai PDF, analyseur d'intention IA sur les 12
   exemples exacts du cahier des charges, 25 index de base de données
   manquants trouvés et corrigés, rate limiting testé avec un vrai délai.
   65 tests automatisés, tous exécutés avec succès.

2. **Cohérent statiquement, jamais exécuté** (la majorité des endpoints
   FastAPI contre une vraie base, le frontend React après npm install,
   les appels réseau Ollama) : syntaxe validée, imports vérifiés à chaque
   phase, mais aucune garantie qu'aucun problème d'exécution ne surgira au
   premier vrai test — c'est structurellement inévitable sans les vrais
   services disponibles pendant la construction.

3. **Documenté comme non fait** plutôt que survolé : écran Utilisateurs,
   export KML depuis l'app, outils de mesure sur la carte, drag & drop
   Kanban, génération d'email par IA, analyse comparative de documents —
   chacun noté explicitement dans la phase concernée avec la raison.

La priorité tout du long a été de ne jamais présenter comme fonctionnel ce
qui ne l'était pas, quitte à ralentir pour tester réellement chaque fois
que c'était possible (Phases 9/11/15/16/17/19/20/21/22/23), et à signaler
clairement la limite chaque fois que ce ne l'était pas.
