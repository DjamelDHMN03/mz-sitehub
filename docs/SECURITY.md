# SECURITY.md — MZ SITEHUB

Synthèse de l'audit de sécurité réalisé en Phase 21 (section 82-83 du
cahier des charges) : ce qui est implémenté, ce qui a été corrigé pendant
cet audit, et ce qui reste à la charge du déploiement (hors du code
applicatif).

## Implémenté et vérifié dans le code

| Exigence (section 82) | Statut | Où |
|---|---|---|
| Authentification | OK | JWT maison, bcrypt (Phase 3) |
| Hash sécurisé | OK | passlib[bcrypt], jamais de mot de passe en clair stocké |
| Sessions | OK | JWT stateless, access 8h / refresh 48h |
| RBAC | OK | require_permission() vérifie côté backend à chaque requête (Phase 3) |
| Validation backend | OK | Schémas Pydantic sur tous les endpoints d'écriture |
| Contrôle uploads | OK | Limite de taille (50 Mo) — corrigé Phase 21 : map_layers et excel_import n'avaient aucune limite avant cet audit |
| Audit | OK | audit_logs, alimenté depuis la Phase 4 par tous les modules |
| Accès privé documents | OK | Téléchargement toujours via route authentifiée, jamais d'URL de stockage brute (Phase 11) |
| Tokens de partage sécurisés | OK | 32 octets d'entropie, jamais devinables (Phase 15) |
| Expiration liens | OK | Revérifiée à CHAQUE accès, pas seulement à la création (Phase 15) |
| Anti path-traversal (stockage) | OK | Testé réellement (Phase 11) |
| Protection brute-force login | OK | Ajouté Phase 21 : 5 échecs / 5 min par email, testé réellement |
| Longueur minimale mot de passe | OK | Ajouté Phase 21 : 8 caractères minimum sur le changement de mot de passe |
| CORS configurable | OK | Corrigé Phase 21 : lu depuis .env (CORS_ALLOWED_ORIGINS), n'était figé en dur que sur localhost:5173 avant |
| En-têtes de sécurité HTTP | OK | Ajouté Phase 21 : X-Content-Type-Options, X-Frame-Options, Referrer-Policy |
| Alerte secret par défaut | OK | Ajouté Phase 21 : avertissement au démarrage si JWT_SECRET n'a pas été changé |

## À la charge du déploiement (pas du code applicatif)

- **HTTPS** : ce backend FastAPI tourne en HTTP simple. En production, un
  reverse proxy (Caddy, recommandé pour son TLS automatique gratuit via
  Let's Encrypt, ou Nginx + Certbot) doit être placé devant, aussi bien pour
  le frontend que pour l'API. Non fait dans cette V1 car ça dépend du nom
  de domaine réel utilisé au déploiement (Phase 24), pas encore connu.
- **Isolation réseau** : en production, la base de données ne devrait pas
  être exposée sur un port public — seul le backend doit pouvoir s'y
  connecter (réseau Docker interne, ce que fait déjà docker-compose.yml
  en dev ; à revérifier sur l'hébergement choisi en Phase 24).
- **Rotation du secret JWT** : JWT_SECRET doit être une valeur aléatoire
  longue et unique par déploiement — jamais celle de .env.example.
  Générable avec `openssl rand -hex 32`.
- **Sauvegardes chiffrées** : la Phase 22 (Backup) couvrira la sauvegarde
  elle-même ; leur chiffrement au repos reste une décision d'hébergement.

## Limites connues de cet audit

- Cet audit couvre le code écrit jusqu'à la Phase 20 inclus. Les phases
  suivantes (22-25) devront être revues avec la même grille avant un
  déploiement réel.
- Le limiteur de connexion (LoginRateLimiter) est en mémoire du process —
  redémarrer le backend réinitialise les compteurs. Acceptable pour une
  V1 mono-instance ; insuffisant si l'attaquant peut provoquer des
  redémarrages.
- Aucun test d'intrusion (pentest) n'a été réalisé — cet audit est une
  revue de code, pas un test de sécurité offensif.
