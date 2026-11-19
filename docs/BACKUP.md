# BACKUP.md — MZ SITEHUB, Sauvegarde et restauration

## Sauvegarde de la base de données

```bash
docker compose exec db pg_dump -U mzsitehub -d mzsitehub -F c -f /tmp/backup.dump
docker compose cp db:/tmp/backup.dump ./backups/mzsitehub_$(date +%Y%m%d).dump
```

Créez un dossier backups/ (ajouté à .gitignore) et lancez cette commande
régulièrement — idéalement via une tâche planifiée (cron sur Linux/Mac,
Planificateur de tâches sur Windows).

## Sauvegarde des documents (GED)

Avec STORAGE_DRIVER=local, tous les fichiers sont dans ./storage/. Une
simple copie suffit :

```bash
tar -czf backups/storage_$(date +%Y%m%d).tar.gz storage/
```

Si vous migrez vers Supabase Storage plus tard (voir docs/DEPLOYMENT.md),
Supabase gère ses propres sauvegardes selon votre plan.

## Export Excel/ZIP (sauvegarde applicative, section 80)

En complément de la sauvegarde technique ci-dessus, l'application permet
d'exporter vos données depuis l'interface :
- Rapports -> export Excel de tous les sites
- Rapports -> export complet (ZIP) par site, avec tous ses documents

Ces exports sont utiles pour une sauvegarde "lisible" indépendante du
format de base de données, mais ne remplacent pas la sauvegarde pg_dump
ci-dessus pour une restauration complète (ils ne contiennent pas
l'historique d'audit, les permissions, etc.).

## Restauration

```bash
docker compose cp ./backups/mzsitehub_20260901.dump db:/tmp/restore.dump
docker compose exec db pg_restore -U mzsitehub -d mzsitehub --clean --if-exists /tmp/restore.dump
```

Attention : --clean supprime les données existantes avant de restaurer —
à utiliser uniquement si vous voulez vraiment remplacer l'état actuel par
celui de la sauvegarde.

## État du dernier backup (section 80)

Non automatisé dans cette version — aucun écran n'affiche la date du
dernier backup réussi. Une implémentation future pourrait enregistrer
chaque backup réussi dans une table dédiée et l'afficher sur le Dashboard.
Pour l'instant, la date figure dans le nom du fichier.

## Recommandation

Avant tout déploiement en production réelle : automatisez la sauvegarde
quotidienne (script + cron) et testez la restauration au moins une fois
sur un environnement de test — une sauvegarde jamais restaurée n'est pas
une sauvegarde fiable.
