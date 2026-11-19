# ARCHITECTURE.md — MZ SITEHUB

## Vue d'ensemble

```
Frontend (React/TS/Vite) <-> Backend (FastAPI/Python) <-> PostgreSQL (+PostGIS +pgvector)
                                      |
                                      +-> Ollama (IA locale, machine séparée)
                                      +-> Stockage fichiers (local ou Supabase Storage)
```

## Backend — organisation des dossiers

```
backend/app/
├── main.py              point d'entrée, enregistrement des routeurs
├── core/                config, sécurité (JWT/bcrypt), permissions RBAC,
│                        audit, limites d'upload, rate limiting
├── db/session.py        connexion SQLAlchemy async
├── models/              ORM SQLAlchemy, un fichier par domaine
├── schemas/             Pydantic — validation entrée/sortie API
├── routers/             endpoints FastAPI, un fichier par domaine
├── services/            logique métier pure (parsing, export, RAG...)
│                        — testable sans base de données
└── ai/                  Assistant IA : provider, intentions, tools
```

Principe suivi tout du long : les fonctions dans services/ ne dépendent
jamais de FastAPI ni de la base de données — elles prennent des données en
entrée et renvoient des résultats, ce qui les rend testables en isolation
(voir docs/TESTING.md). Les routers/ orchestrent : authentification,
requête DB, appel aux services, réponse HTTP.

## Base de données

Deux migrations SQL, appliquées dans l'ordre :
- 001_init_core_schema.sql : 32 tables (schéma complet initial)
- 002_add_missing_indexes.sql : 25 index sur les clés étrangères
  (ajout Phase 23, jamais de modification rétroactive de la 001)

Extensions PostgreSQL utilisées : pgcrypto (UUID), postgis (géométries),
pg_trgm (recherche floue sur les codes), pgvector (embeddings RAG).

## Frontend — organisation des dossiers

```
frontend/src/
├── components/    Button, Card, Table, Badge... — Design System
├── layout/        Sidebar, Navbar, MainLayout
├── pages/         une page par écran
├── lib/           client API (axios), contexte d'authentification, types
└── styles/        tokens.css (palette dérivée du logo), global.css
```

## Flux d'authentification

1. POST /auth/login -> JWT access (8h) + refresh (48h)
2. Chaque requête protégée passe par get_current_user (décode le JWT,
   vérifie l'utilisateur en base)
3. require_permission(resource, level) vérifie en plus le rôle contre
   roles.permissions — jamais uniquement côté frontend
4. À l'expiration de l'access token, le frontend rafraîchit automatiquement
   via le refresh token (voir frontend/src/lib/api.ts)

## Abstractions clés (pour changer de fournisseur sans réécrire l'app)

- app/services/storage.py — StorageProvider : local aujourd'hui, Supabase
  Storage possible sans changer les routeurs
- app/ai/provider.py — AIProvider : Ollama (local, par défaut) ou API
  externe si une clé est explicitement fournie

## Pourquoi certaines décisions ont été prises

- JWT maison plutôt que Supabase Auth (Phase 3, décision validée avec
  l'utilisateur) : contrôle total du RBAC, 0 DA garanti
- Moteur à règles pour l'Assistant IA en plus du LLM (Phase 19) : garantit
  que les commandes structurées fonctionnent même si Ollama n'est jamais
  configuré
- Pas de drag & drop sur le Kanban (Phase 14) : le déplacement via
  PATCH /sites/{id} déjà existant évite d'ajouter une dépendance et une
  complexité non indispensables en V1
