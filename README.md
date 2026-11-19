# MZ SITEHUB

Plateforme d'acquisition de sites télécoms — MZ Building × Ooredoo Algérie.
GIS • GED • CRM • Contrats • Workflow • Collaboration • IA.

## Stack (100% gratuit / Open Source pour la V1)

| Couche | Techno |
|---|---|
| Frontend | React + TypeScript + Vite + Tailwind |
| Backend | Python + FastAPI + Pydantic |
| Base de données | PostgreSQL + PostGIS + pgvector |
| Auth | JWT (bcrypt) |
| Carte | Leaflet + OpenStreetMap |
| Stockage documents | Local (V1) avec abstraction vers Supabase Storage |
| IA | Ollama (modèle local) via une couche `AIProvider` |

## Démarrage rapide

Voir **[docs/INSTALLATION.md](docs/INSTALLATION.md)** pour le guide pas à pas complet.

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec backend python -m scripts.seed_admin --email vous@exemple.com --password "..."
```

- Frontend : http://localhost:5173
- Backend (Swagger) : http://localhost:8000/docs

## Documentation

| Document | Contenu |
|---|---|
| [INSTALLATION.md](docs/INSTALLATION.md) | Installation locale pas à pas |
| [USER_GUIDE.md](docs/USER_GUIDE.md) | Guide utilisateur non technique |
| [ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md) | Gestion des utilisateurs, rôles, statuts |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Organisation du code, flux d'authentification |
| [SECURITY.md](docs/SECURITY.md) | Audit de sécurité complet |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Déploiement gratuit (Cloudflare/Render/Supabase) |
| [BACKUP.md](docs/BACKUP.md) | Sauvegarde et restauration |
| [AI.md](docs/AI.md) | Assistant IA et RAG |
| [CARTOGRAPHY.md](docs/CARTOGRAPHY.md) | Carte, import KMZ/KML |
| [TESTING.md](docs/TESTING.md) | Suite de tests (65 tests), comment lancer |
| [ROADMAP.md](docs/ROADMAP.md) | Détail technique de chacune des 25 phases de construction |

## État d'avancement — 25/25 phases

Le projet a été construit **par phases**, chaque phase livrant du code réel
et vérifié avant de passer à la suivante, plutôt qu'une génération unique
impossible à valider dans son ensemble.

- [x] Phase 1 — Architecture & structure du projet
- [x] Phase 2 — Base de données (32 tables)
- [x] Phase 3 — Authentification & rôles (JWT + RBAC)
- [x] Phase 4 — Backend Sites (CRUD, corbeille, audit, historique code)
- [x] Phase 5 — Frontend + Design System
- [x] Phase 6 — Dashboard (statistiques temps réel)
- [x] Phase 7 — Sites (couvert dès la Phase 4)
- [x] Phase 8 — Carte interactive (Leaflet + OSM, clustering)
- [x] Phase 9 — Import KMZ/KML (**testé sur un vrai fichier fourni**, 25 sites, bug trouvé et corrigé)
- [x] Phase 10 — Contacts / CRM
- [x] Phase 11 — Documents / GED (**testé réellement** : stockage, reconnaissance de fichiers)
- [x] Phase 12 — Doc B / APS
- [x] Phase 13 — Contrats
- [x] Phase 14 — Actions / Kanban / Calendrier
- [x] Phase 15 — Partage documentaire (**testé réellement** : tokens, expiration, ZIP)
- [x] Phase 16 — Import Excel (**testé sur un vrai fichier .xlsx**)
- [x] Phase 17 — Rapports / Exports (**testé réellement**, PDF avec les vrais logos)
- [x] Phase 18 — Historique / Audit
- [x] Phase 19 — Assistant IA (**moteur à règles testé** sur 12 exemples exacts du cahier des charges)
- [x] Phase 20 — RAG (**extraction/chunking testés réellement** sur un vrai PDF)
- [x] Phase 21 — Sécurité (audit réel, 3 trous corrigés)
- [x] Phase 22 — Tests (**65/65 tests exécutés ensemble**)
- [x] Phase 23 — Optimisation (25 index manquants trouvés et corrigés)
- [x] Phase 24 — Déploiement gratuit (limites vérifiées par recherche web)
- [x] Phase 25 — Documentation

Détail complet de chaque phase (décisions techniques, bugs trouvés,
limites assumées) : [docs/ROADMAP.md](docs/ROADMAP.md).

## Limites connues, honnêtement

Ce projet a été construit dans un environnement sans accès réseau pour
installer les dépendances Python/Node, et sans base Postgres ni Ollama
réellement démarrés. Deux catégories de fiabilité en découlent :

- **Testé pour de vrai** (parsing KML, reconnaissance de documents,
  import Excel, génération PDF/CSV/Excel, tokens de partage, chunking RAG,
  analyseur d'intention IA, rate limiting) — 65 tests exécutés avec succès,
  plusieurs bugs réels trouvés et corrigés pendant la construction.
- **Cohérent statiquement mais jamais exécuté** (tous les endpoints FastAPI
  contre une vraie base Postgres, les appels réseau vers Ollama, le build
  npm du frontend) — syntaxe et imports vérifiés à chaque phase, mais le
  premier vrai test contre Docker chez vous révélera probablement des
  ajustements, comme pour n'importe quel projet de cette taille.

Voir [docs/TESTING.md](docs/TESTING.md) pour le détail précis de cette
frontière, phase par phase.

## Règle sur les données

Aucune donnée (GPS, téléphone, montant, statut juridique...) n'est jamais
inventée. Toute information inconnue est `NULL` ou marquée `À COMPLÉTER`.

## Identité visuelle

La palette (`frontend/src/styles/tokens.css`) est extraite automatiquement
du dégradé du logo MZ Building : violet profond `#3D2140` → magenta
`#AE2858`. Dark mode par défaut.
