# Migration 2026-10 — Consolidation des rôles (admin unique + apprenants)

Environnement : **préproduction uniquement** (base `DB_NAME` de cet environnement). Aucune mise en production.

## 1. Sauvegarde (avant toute modification)
```bash
cd /app/backend && set -a && . ./.env && set +a
mongodump --uri "$MONGO_URL" --db "$DB_NAME" --archive=/app/backups/pre_roles_<horodatage>.gz --gzip
chmod 600 /app/backups/pre_roles_<horodatage>.gz
```
- Archive réalisée : `/app/backups/pre_roles_20261021T004637Z.gz` (droits 600, dossier 700, exclu de git via `.gitignore`).
- Test de restauration : `mongorestore --nsFrom "$DB_NAME.*" --nsTo "${DB_NAME}_restore_test.*"` → 37 collections, 1 047 documents, **0 écart** d'effectifs ni d'index ; base de test supprimée ensuite.
- Effectifs avant : `/app/backups/counts_before.txt`.

## 2. Ordre d'exécution suivi
1. Sauvegarde et test de restauration.
2. Déploiement du code : champ `role`, permissions admin/learner, `require_learner`, `session_version`, protections, seeds sans comptes de rôles et sans resynchronisation des mots de passe. Tant que la migration n'est pas appliquée, le seed ne crée rien (garde-fou).
3. `python3 scripts/migrate_2026_10_roles.py` (dry-run) → `--apply` → `--apply` (2e passage : « Aucune modification »).
4. `python3 scripts/migrate_2026_10_roles.py --index` → index unique partiel `unique_single_admin` sur `{ role: 1 }`, filtre `{ role: "admin" }`.
5. Redémarrage du backend : empreinte SHA-256 des 49 comptes identique avant et après (aucun compte recréé ni modifié).

## 3. Ce que fait la migration (idempotente, journalisée)
| Compte | Avant | Après |
|---|---|---|
| admin@casa-academy.ci (même `_id`) | roles [admin, learner] | email **admin@casa-academy.com**, role admin, legacy_roles [admin, learner], session_version +1 ; mot de passe, nom et demo_progress inchangés |
| evaluator@, author@, reviewer@, lead@ | un rôle de personnel chacun | role learner, active=false, legacy_roles conservés, session_version +1 |
| 44 apprenants (dont les 39 comptes QA) | roles [learner] | role learner, legacy_roles [learner] ; actif et sessions inchangés |

- Le champ `roles` est retiré (`$unset`) ; `legacy_roles` garde l'historique, sans valeur de permission.
- 5 entrées `role_migration` dans `catalog_change_log` ; marqueur `migrations._id = "2026_10_roles"` avec le rapport et la liste des passages.
- Les blocages de connexion de l'ancien email admin sont supprimés.

## 4. Données préservées
- Journal : les 110 entrées antérieures sont intactes (auteurs author@, lead@, reviewer@ et admin@ lisibles).
- Projets M16 : `review.evaluator_name` intact ; certificats : 6 révoqués, toujours révoqués ; inscriptions, progressions, tentatives et acquis inchangés.
- Bilan après tests et nettoyage : seules diffèrent `catalog_change_log` (110 → 160 : migration et scénarios de test du circuit éditorial), `events` (39 → 43, tests anonymes), `login_attempts` (5 → 6) et `migrations` (0 → 1).
- Références orphelines : 8 `resource_progress` et 1 `attempts` pointent vers 2 comptes inexistants ; **elles existaient déjà dans la sauvegarde d'avant migration** (vérifié en restauration isolée), sans correction.

## 5. Retour arrière
1. Code : `git revert` des commits de la consolidation.
2. Données, sans la sauvegarde : pour chaque compte, `roles = legacy_roles`, `email` admin remis en `.ci`, `active=true` pour les 4 comptes retirés ; supprimer l'index `unique_single_admin` et le marqueur `migrations`.
3. Données, avec la sauvegarde (dernier recours, perd l'activité postérieure) :
```bash
mongorestore --uri "$MONGO_URL" --archive=/app/backups/pre_roles_20261021T004637Z.gz --gzip --drop \
  --nsInclude "$DB_NAME.users" --nsInclude "$DB_NAME.catalog_change_log" --nsInclude "$DB_NAME.migrations"
```
4. Redémarrer le backend.

## 6. Nettoyage des données de test
`scripts/cleanup_test_runs.py <horodatage ISO>` supprime les contenus `test-*`, `QA-*` et `qa-*`, les brouillons et les comptes de test créés après l'horodatage donné (le journal est conservé). Les 39 comptes QA antérieurs n'ont pas été touchés.
