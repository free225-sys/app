# Rapprochement — suppression accidentelle puis recréation de M-001 v2

Préproduction (base test_database). Document rédigé le 22/10/2026 à partir du journal (catalog_change_log), des instantanés de /app/backups et de l'historique git des scripts. Aucune donnée n'a été modifiée pour le rédiger.

## 1. Chronologie (UTC)

| Heure | Événement | Source |
|---|---|---|
| 21/10 09:12:18 | M-001 v2 créée à partir de v1 (`new_version`, v2), par l'administrateur, script `scripts/drafts/cert_doc_01_drafts.py` (commit e7e9094, 09:13) | journal |
| 21/10 09:12:18 | M-001 v2 soumise à relecture (`submit`, v2) | journal |
| 21/10 09:12 | Instantané `cert_doc_after.json` : M-001 latest_version = 2, published_version = 1 | /app/backups |
| 21/10 14:32 | Instantané `cert_doc_before2.json` : M-001 latest_version = 2 (le brouillon existe encore) | /app/backups |
| 21/10 14:34:18 → 14:34:22 | Une suite de tests automatisés crée des brouillons de test : test-concept-d6f5e6, test-cyc-a/b-d6f5e6, M09 v2 | journal |
| 21/10 entre 14:34:22 et 14:34:58 | `cleanup_test_runs.py <horodatage ISO du début de la session de tests>` supprime M-001 v2 avec les brouillons de test | déduit : absence de journal (suppression directe en base), état avant/après |
| 21/10 14:34:58 | M-001 v2 recréée par le circuit normal (`new_version` puis `submit`, v2) | journal |
| 21/10 14:36:20 → 14:36:23 | Nouvelle série de tests : test-concept-916ea8, test-cyc-a/b-916ea8, M09 v2 | journal |
| 21/10 ~14:37 | Second passage du script corrigé : supprime M09 v2 de test, 3 notions `test-*` et 6 comptes de test ; M-001 v2 est épargnée | sortie conservée du script |
| 21/10 14:49 | Script durci : liste blanche obligatoire (commit 659f9a3) | git |

La commande exacte du premier passage, avec son horodatage, n'a pas été conservée. Sa sortie n'a pas été gardée non plus. Le filtre en cause, lui, est connu par la version du script de ce commit (fa7f961).

## 2. Cause exacte du filtre

La version d'origine du script supprimait, dans `concept_versions` et `module_versions`, **toutes** les versions en brouillon ou en relecture créées après l'horodatage donné :

```
db[coll].find({"status": {"$in": ["draft", "review"]}, "created_at": {"$gte": since}})
```

Ce filtre ne tenait compte ni du préfixe `test-`, ni de l'auteur, ni d'une liste d'éléments. M-001 v2 avait été créée à 09:12:18, après l'horodatage passé au script : elle remplissait donc les conditions de suppression. La suppression était faite directement en base, sans passer par l'API ; elle n'a donc laissé aucune entrée au journal.

## 3. Comparaison champ par champ

- **Document supprimé** : il a été reconstitué. La source est le script de création (`cert_doc_01_drafts.py`, git) : contenu de v1 plus `levels = [L0, L1]`, `assessment_ids = [A-M-001-F, A-M-001-G]` et `completion_rule = resources_and_graded`. Le journal (`new_version` de v2 à partir de v1 publiée) et l'instantané de 14:32 (latest_version = 2) confirment cette reconstitution.
- **Document recréé** : M-001@2 tel qu'il figure dans la base.

| Champ | Supprimé (reconstitué) | Recréé | Écart |
|---|---|---|---|
| 14 champs de contenu (titre, code, ressources, notions, compétences, couches, étapes, prérequis, etc.) | identiques à v1, sauf les 3 champs ci-dessous | identiques | aucun |
| levels | [L0, L1] | [L0, L1] | aucun |
| assessment_ids | [A-M-001-F, A-M-001-G] | [A-M-001-F, A-M-001-G] | aucun |
| completion_rule | resources_and_graded | resources_and_graded | aucun |
| _id (identifiant interne) | M-001@2 | M-001@2 | aucun (identifiant déterministe) |
| created_at | 2026-10-21T09:12:18 | 2026-10-21T14:34:58 | **perdu** |
| submitted_at | 2026-10-21T09:12:18 | 2026-10-21T14:34:58 | **perdu** |
| created_by / submitted_by | administrateur | administrateur | aucun |
| changelog | « CERT-DOC-01 option B : quiz noté K-001 pour M-001 (brouillon, à valider par le client) » | même texte suivi de « — recréé à l'identique après suppression accidentelle par le script de nettoyage » | volontaire |
| reviews (relectures et commentaires) | [] | [] | aucun (aucune relecture ni aucun commentaire n'avait eu lieu : 0 entrée approve/return au journal) |
| status / approved | review / non | review / non | aucun |

Les deux entrées de journal d'origine (09:12:18) sont conservées.

## 4. Autres entités touchées

Toutes les créations de notions, de modules et de ressources journalisées le 21/10 entre 00:46 et 14:38 ont été vérifiées dans la base :

- **Absentes, toutes de test** :
  - les notions test-concept-*, test-cyc-a-* et test-cyc-b-* (séries 53b732, 08cdd6, d6f5e6 et 916ea8) ;
  - les notions test-c-*, dont la suppression par l'API est journalisée ;
  - M09 v2, trois fois (brouillon de test créé par les suites).
- **Entités hors test supprimées** : aucune, à part M-001 v2.
- **Autres brouillons CERT-DOC-01** : non touchés, car le script ne traitait pas ces collections. Leur date de création d'origine le prouve : CO-001 v2 à 09:12:18, CO-002 v2 à 09:12:19 et A-M-001-G v1 à 09:12:18. Les questions G1 à G5 et les parcours P-001 et P-002 v2 ne sont pas concernés non plus.
- **Comptes** : seuls ont été supprimés des comptes de test créés par les suites du jour, au filtre `^(test|qa)` et à une date de création postérieure à l'horodatage. La vérification du 21/10 a confirmé que les 39 comptes QA plus anciens sont présents et inchangés (empreintes identiques à la sauvegarde).

## 5. Mesures prises

- `cleanup_test_runs.py` refuse de s'exécuter sans `--whitelist <fichier>`. Il ne supprime que les éléments listés (`id@version`) et exclut en plus tout brouillon portant la mention CERT-DOC-01.
- Consigne du client en vigueur : aucun nettoyage sans son accord sur la liste exacte.
- Les suites de tests qui écrivent refusent de tourner sur test_database. Le garde-fou se trouve dans `tests/conftest.py` et s'appuie sur DB_NAME et CASA_TEST_DB.
- Les tests de bout en bout se font uniquement sur une base isolée (casa_e2e, casa_e2e_revoc), servie par une instance distincte sur le port 8002.
