# INSTALLATION.md — MZ SITEHUB

Installation locale, pas à pas, pour Windows/Mac/Linux avec Docker.

## Prérequis

- Docker Desktop installé et démarré (Windows, Mac ou Linux)
- Au moins 8 Go de RAM disponibles (plus si vous comptez faire tourner
  Ollama pour l'Assistant IA en local également)
- Git (pour récupérer le projet)

## Étapes

### 1. Récupérer le projet

```bash
git clone <url-de-votre-dépôt> MZ-SITEHUB
cd MZ-SITEHUB
```

Ou, si vous avez reçu une archive .zip, décompressez-la simplement.

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Ouvrez .env avec un éditeur de texte et changez au minimum JWT_SECRET
(section Sécurité) — générez une vraie valeur aléatoire :

```bash
openssl rand -hex 32
```

Copiez le résultat dans .env à la place de change_moi_en_production.

### 3. Démarrer l'application

```bash
docker compose up -d --build
```

Premier démarrage : 3 à 5 minutes (téléchargement des images, installation
des dépendances). Les démarrages suivants sont quasi instantanés.

### 4. Créer votre premier compte administrateur

```bash
docker compose exec backend python -m scripts.seed_admin \
  --email votre-email@exemple.com \
  --password "un-mot-de-passe-solide" \
  --first-name VotrePrenom --last-name VotreNom
```

### 5. Ouvrir l'application

- Interface : http://localhost:5173
- Documentation technique de l'API : http://localhost:8000/docs

Connectez-vous avec l'email/mot de passe de l'étape 4.

## Vérifier que tout fonctionne

```bash
curl http://localhost:8000/health
```
Doit répondre {"status":"ok","service":"mz-sitehub-backend"}.

## Arrêter l'application

```bash
docker compose down
```
Vos données restent sur votre disque (volumes Docker) — un
docker compose up -d ultérieur les retrouve intactes.

## Problèmes fréquents

| Symptôme | Cause probable | Solution |
|---|---|---|
| Port 5173 ou 8000 déjà utilisé | Une autre application tourne dessus | Fermez-la, ou changez le port dans docker-compose.yml |
| "Cannot connect to Docker daemon" | Docker Desktop n'est pas démarré | Lancez Docker Desktop et réessayez |
| La carte n'affiche pas de tuiles | Pas de connexion Internet | OpenStreetMap nécessite Internet |
| L'Assistant IA répond "je n'ai pas compris" à tout | Normal sans Ollama | Les commandes structurées fonctionnent déjà sans Ollama — voir docs/AI.md |

Pour tout autre problème, copiez le message d'erreur exact de
docker compose logs backend ou docker compose logs frontend.
