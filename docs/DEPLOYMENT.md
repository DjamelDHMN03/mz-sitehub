# DEPLOYMENT.md — MZ SITEHUB, déploiement à 0 DA

Vérifié le 2 septembre 2026 (les limites des offres gratuites changent
souvent — revérifiez sur les sites officiels avant de vous engager si vous
lisez ceci plus tard).

## Vue d'ensemble

| Composant | Service gratuit | Limite principale à connaître |
|---|---|---|
| Frontend (React) | Cloudflare Pages | Bande passante illimitée, 500 builds/mois — largement suffisant |
| Backend (FastAPI) | Render Free | 512 Mo de RAM, se met en veille après 15 min d'inactivité (premier appel après veille = 30-60s) |
| Base de données | Supabase Free | 500 Mo de stockage, projet mis en pause après 7 jours d'inactivité, PostGIS et pgvector inclus nativement |
| IA (Ollama) | Votre propre machine | Ni Render ni Cloudflare ne peuvent faire tourner un modèle 8B (RAM insuffisante) |
| Carte | OpenStreetMap + Leaflet | Déjà gratuit, aucun compte requis |

Aucune de ces limites n'a pu être testée en conditions réelles ici — je
n'ai pas de compte sur ces services. Ce document donne la configuration
prête à l'emploi ; le premier déploiement réel révélera sûrement des
ajustements, comme pour chaque phase précédente de ce projet.

## 1. Base de données — Supabase Free

1. Créer un compte sur supabase.com, nouveau projet (gratuit)
2. Dans le SQL Editor, exécuter dans l'ordre :
   - database/migrations/001_init_core_schema.sql
   - database/migrations/002_add_missing_indexes.sql
3. Récupérer la chaîne de connexion : Project Settings > Database >
   Connection String > Session pooler (pas "Direct connection", qui ne
   fonctionne pas depuis un environnement serverless/PaaS comme Render)
4. Point de vigilance réel : un projet Supabase gratuit se met en pause
   après 7 jours sans activité. Pour un usage réellement quotidien, soit
   vous acceptez de le réactiver manuellement à l'occasion (gratuit, un
   clic), soit vous passez au plan payant (~25 USD/mois).

## 2. Backend — Render Free

1. Pousser ce projet sur GitHub
2. Sur render.com : New > Blueprint > sélectionner le repo > Render
   détecte render.yaml à la racine
3. Renseigner les variables marquées sync: false :
   - DATABASE_URL : la chaîne de connexion Supabase de l'étape 1
   - OLLAMA_BASE_URL : l'URL publique de votre machine qui fait tourner
     Ollama (voir section 4) — nécessite d'exposer le port 11434 de façon
     sécurisée (tunnel type Cloudflare Tunnel ou ngrok, jamais ouvert
     directement sur Internet sans authentification)
   - CORS_ALLOWED_ORIGINS : l'URL Cloudflare Pages (étape 3)
4. Point de vigilance réel, découvert en recherchant les limites actuelles :
   le plan gratuit de Render a un stockage disque ÉPHÉMÈRE — tout fichier
   écrit par STORAGE_DRIVER=local (Phase 11) est perdu à chaque
   redéploiement ou redémarrage du conteneur. Ce n'est pas acceptable pour
   la GED en production. Deux options :
   - passer un plan Render payant avec disque persistant, ou
   - fournir une clé Supabase Storage et implémenter réellement
     SupabaseStorageProvider (squelette posé en Phase 11, non implémenté
     faute de clé à tester) — voie recommandée pour rester à 0 DA
5. Point de vigilance : 512 Mo de RAM est serré avec FastAPI + SQLAlchemy +
   reportlab + pypdf + openpyxl + shapely. Un crash mémoire (OOM) après
   quelques requêtes signale qu'il faut alléger les dépendances ou passer
   un plan payant.

## 3. Frontend — Cloudflare Pages

1. Sur dash.cloudflare.com > Workers & Pages > Create > Pages > Connect to
   Git > sélectionner le repo
2. Configuration du build :
   - Répertoire racine : frontend
   - Commande de build : npm run build
   - Répertoire de sortie : dist
3. Variable d'environnement : VITE_API_BASE_URL = URL Render de l'étape 2
4. Cloudflare Pages fournit un sous-domaine *.pages.dev gratuit ; un vrai
   domaine peut être ajouté ensuite gratuitement si vous en possédez un.

## 4. IA — Ollama sur votre propre machine (rappel Phase 19)

Ollama ne peut pas tourner sur Render/Cloudflare (RAM insuffisante pour un
modèle 8B). Il doit tourner sur une machine que vous contrôlez :

```bash
ollama serve
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Pour que le backend déployé sur Render puisse l'atteindre, exposez le port
11434 via un tunnel sécurisé plutôt qu'en l'ouvrant directement :

```bash
cloudflared tunnel --url http://localhost:11434
```

Sans cette étape, l'Assistant IA continue de fonctionner via le moteur à
règles déterministe (Phase 19) — seule la partie LLM/RAG conversationnelle
reste indisponible tant qu'Ollama n'est pas joignable.

## 5. Garder les services gratuits "éveillés" (optionnel)

```yaml
# .github/workflows/keep-alive.yml (à créer si souhaité)
name: Keep services alive
on:
  schedule:
    - cron: "*/10 * * * *"
jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - run: curl -sf https://mz-sitehub-backend.onrender.com/health
```

GitHub Actions est gratuit pour les dépôts publics (2000 min/mois pour les
dépôts privés) — largement suffisant pour ce ping.

## Ce qui n'a pas pu être vérifié ici

Aucun compte Cloudflare/Render/Supabase n'existe dans cet environnement de
construction — rien de ce document n'a été testé par un déploiement réel.
Les limites citées viennent d'une recherche web datée du 2 septembre 2026
(sources : documentation officielle Render, Cloudflare, Supabase, et
retours d'expérience développeurs). Le premier vrai déploiement révélera
sûrement des ajustements — dites-le-moi à ce moment-là avec le message
d'erreur exact plutôt que de deviner une solution à l'avance.
