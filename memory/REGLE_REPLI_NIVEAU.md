# Règle de repli — niveau évalué des quiz déjà publiés

Préproduction. Décision du client du 22/10/2026 : règle de repli calculée **sans écriture en base**, pas de migration. Elle ne s'applique que si l'interrupteur CASA_LEVEL_FROM_ASSESSMENT_MODULE_VERSION vaut 1 (désactivé sur la préproduction partagée).

## Règle exacte

Pour une version d'évaluation publiée qui ne porte pas de module_version :
1. on prend les versions du même module (module_id de la version d'évaluation) qui ont une date de publication ;
2. on retient la **dernière** dont la date de publication est **antérieure ou égale** à la date de publication de la version d'évaluation ;
3. à défaut (module publié après l'évaluation), on retient la **première** version publiée du module ;
4. niveau évalué = niveau maximal de la version de module retenue (ordre L0 < L1 < L2 < L3 < L4).

Une version d'évaluation qui porte module_version (brouillons actuels, futures publications) utilise toujours cette valeur figée ; la règle de repli ne s'applique pas.
La règle est déterministe et figée : elle ne lit que des dates de publication passées, qui ne changent plus. Implémentation : `evaluated_module_version` dans backend/learning.py.

## Résultat actuel (35 versions d'évaluation publiées, calcul en lecture seule)

| Évaluation | Version | Type | Module | Version de module retenue | Niveau évalué | Publication de l'évaluation |
|---|---|---|---|---|---|---|
| A-DIAG | v1 | diagnostic | — | non applicable | — | 2026-09-01 |
| A-M-001-F | v1 | formative | M-001 | v1 | L0 | 2026-09-01 |
| A-M-003-G | v1 | graded | M-003 | v1 | L1 | 2026-09-01 |
| A-M01-F | v1 | formative | M01 | v1 | L0 | 2026-09-01 |
| A-M01-G | v1 | graded | M01 | v1 | L0 | 2026-09-01 |
| A-M02-F | v1 | formative | M02 | v1 | L1 | 2026-09-01 |
| A-M02-G | v1 | graded | M02 | v1 | L1 | 2026-09-01 |
| A-M03-F | v1 | formative | M03 | v1 | L2 | 2026-09-01 |
| A-M03-G | v1 | graded | M03 | v1 | L2 | 2026-09-01 |
| A-M04-F | v1 | formative | M04 | v1 | L3 | 2026-09-01 |
| A-M04-G | v1 | graded | M04 | v1 | L3 | 2026-09-01 |
| A-M05-F | v1 | formative | M05 | v1 | L3 | 2026-09-01 |
| A-M05-G | v1 | graded | M05 | v1 | L3 | 2026-09-01 |
| A-M06-F | v1 | formative | M06 | v1 | L3 | 2026-09-01 |
| A-M06-G | v1 | graded | M06 | v1 | L3 | 2026-09-01 |
| A-M07-F | v1 | formative | M07 | v1 | L3 | 2026-09-01 |
| A-M07-G | v1 | graded | M07 | v1 | L3 | 2026-09-01 |
| A-M08-F | v1 | formative | M08 | v1 | L3 | 2026-09-01 |
| A-M08-G | v1 | graded | M08 | v1 | L3 | 2026-09-01 |
| A-M09-F | v1 | formative | M09 | v1 | L3 | 2026-09-01 |
| A-M09-G | v1 | graded | M09 | v1 | L3 | 2026-09-01 |
| A-M10-F | v1 | formative | M10 | v1 | L3 | 2026-09-01 |
| A-M10-G | v1 | graded | M10 | v1 | L3 | 2026-09-01 |
| A-M11-F | v1 | formative | M11 | v1 | L4 | 2026-09-01 |
| A-M11-G | v1 | graded | M11 | v1 | L4 | 2026-09-01 |
| A-M12-F | v1 | formative | M12 | v1 | L3 | 2026-09-01 |
| A-M12-G | v1 | graded | M12 | v1 | L3 | 2026-09-01 |
| A-M13-F | v1 | formative | M13 | v1 | L3 | 2026-09-01 |
| A-M13-G | v1 | graded | M13 | v1 | L3 | 2026-09-01 |
| A-M14-F | v1 | formative | M14 | v1 | L4 | 2026-09-01 |
| A-M14-G | v1 | graded | M14 | v1 | L4 | 2026-09-01 |
| A-M15-F | v1 | formative | M15 | v1 | L3 | 2026-09-01 |
| A-M15-G | v1 | graded | M15 | v1 | L3 | 2026-09-01 |
| A-M16-F | v1 | formative | M16 | v1 | L3 | 2026-09-01 |
| A-M16-G | v1 | graded | M16 | v1 | L3 | 2026-09-01 |

## Limites

- 35 versions d'évaluation publiées existent aujourd'hui (le chiffre de 38 donné précédemment était inexact). A-DIAG (diagnostic) n'est rattachée à aucun module : non applicable, il ne produit ni tentative notée ni acquis.
- Toutes les versions publiées actuelles (évaluations et modules) datent du 2026-09-01 : le repli retient donc la v1 de chaque module. Deux publications le même jour sont départagées par l'horodatage complet ; à égalité stricte, la version d'évaluation est rattachée à la version de module publiée au même instant.
- Le repli s'appuie sur les dates de publication des versions (published_at), pas sur le journal ; si une date était corrigée à la main en base, le résultat changerait.
- Les quiz formatifs n'enregistrent pas de tentative : le niveau évalué ne les concerne pas en pratique.
- Les tentatives et acquis déjà enregistrés ne sont pas recalculés ; ils n'ont pas de module_version ni de level_evaluated.
