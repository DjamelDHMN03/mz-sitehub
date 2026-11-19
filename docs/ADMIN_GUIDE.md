# ADMIN_GUIDE.md — MZ SITEHUB, guide administrateur

Réservé aux comptes avec le rôle ADMIN.

## Gestion des utilisateurs

Actuellement via l'API (/docs Swagger) ou directement en base — l'écran
dédié "Utilisateurs" du menu (section 12) n'a pas encore d'interface web
construite. En attendant :

```bash
docker compose exec backend python -m scripts.seed_admin \
  --email nouveau@exemple.com --password "..." \
  --first-name Prenom --last-name Nom
```
(le script crée toujours un compte ADMIN — pour un autre rôle, changer le
role_id directement en base ou via un futur écran dédié)

Pour désactiver un compte (jamais le supprimer) :
```sql
UPDATE users SET is_active = false WHERE email = 'compte@exemple.com';
```

## Gestion des rôles et permissions

Les 4 rôles (ADMIN, MANAGER, ACQUISITION, LECTURE) et leurs permissions
sont définis dans roles.permissions (JSON), initialisés par la migration
001. Pour changer les permissions d'un rôle :

```sql
UPDATE roles SET permissions = '{"sites": "write", "contacts": "write"}'
WHERE code = 'MANAGER';
```

Niveaux possibles par ressource : "read", "write_own", "write", ou
"all": true pour un accès total (réservé à ADMIN).

## Gestion des statuts de site (section 53)

Les 23 statuts par défaut sont dans la table site_status. Pour en ajouter
un, le renommer, changer sa couleur ou son ordre :

```sql
INSERT INTO site_status (code, label, color, sort_order)
VALUES ('MON_STATUT', 'Mon Statut', '#4C9FE8', 24);

UPDATE site_status SET color = '#FF0000' WHERE code = 'BLOQUE';

UPDATE site_status SET is_active = false WHERE code = 'ANCIEN_STATUT';
```
Un écran d'administration dédié n'a pas encore été construit — ces
opérations passent par SQL direct pour l'instant.

## Sauvegardes

Voir docs/BACKUP.md pour la procédure complète.

## Supervision

- Logs backend : docker compose logs -f backend
- Logs frontend : docker compose logs -f frontend
- Santé de l'API : curl http://localhost:8000/health
- Historique des actions : écran Historique dans l'application, ou
  directement la table audit_logs

## Sécurité

Voir docs/SECURITY.md pour l'audit complet. Actions à faire avant tout
déploiement accessible publiquement :
1. Changer JWT_SECRET dans .env (jamais la valeur d'exemple)
2. Configurer CORS_ALLOWED_ORIGINS avec le(s) vrai(s) domaine(s)
3. Mettre HTTPS en place via un reverse proxy (voir docs/DEPLOYMENT.md)

## Restaurer un site supprimé (corbeille)

```bash
curl http://localhost:8000/sites/trash -H "Authorization: Bearer $TOKEN"
curl -X POST http://localhost:8000/sites/{id}/restore -H "Authorization: Bearer $TOKEN"
```
La suppression définitive (DELETE /sites/{id}/permanent) est réservée au
rôle ADMIN et n'est possible qu'après passage préalable en corbeille.
