# Récupération de l'accès administrateur (préproduction et production)

Le modèle compte **un seul administrateur**, garanti par l'index unique partiel `unique_single_admin` sur `users.role` (filtre `role: "admin"`). L'interface ne permet ni de désactiver, ni de rétrograder, ni de réinitialiser ce compte. En cas de perte d'accès, la seule voie est le script serveur ci-dessous.

## Prérequis
- Accès shell au serveur backend (le même environnement que `backend/.env`, qui fournit `MONGO_URL` et `DB_NAME`).
- Aucune valeur secrète n'est passée en argument : le mot de passe est saisi de façon interactive (getpass), ou lu sur l'entrée standard pour une automatisation.

## Commandes
```bash
cd /app/backend
# 1. Vérifier sans rien modifier
python3 scripts/admin_recover.py --email admin@casa-academy.com --dry-run
# 2. Redéfinir le mot de passe de l'administrateur (saisie masquée, avec confirmation)
python3 scripts/admin_recover.py --email admin@casa-academy.com --set-password
# 3. Transférer le rôle à un autre compte existant (il doit déjà exister comme apprenant)
python3 scripts/admin_recover.py --email nouvelle.personne@exemple.org --set-password
```

## Effets
- Si un autre compte est administrateur, il est d'abord rétrogradé en apprenant (et sa `session_version` est incrémentée), puis la cible est promue. L'index empêche tout état à deux administrateurs.
- La cible est réactivée (`active=true`). Sa `session_version` est incrémentée, ce qui invalide toutes ses sessions ouvertes. Son blocage de connexion par email est levé.
- Chaque opération est inscrite dans `catalog_change_log` (`action=admin_recover`, `user_email=cli-admin-recover`), **sans le mot de passe**.

## À valider avant la production
- Désigner les personnes autorisées à exécuter le script, et le canal d'accès au serveur.
- Tester la procédure une fois sur la préproduction après chaque déploiement.
