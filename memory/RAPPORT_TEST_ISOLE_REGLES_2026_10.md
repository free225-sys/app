# Rapport — test isolé des règles 2026-10 (niveau évalué, tentatives supplémentaires)

Préproduction, 22/10/2026. Aucun secret, jeton ni mot de passe ne figure dans ce rapport.

## 1. Interrupteurs et preuve de non-régression en préproduction

| Interrupteur | Effet quand il vaut 1 | Préproduction (8001) | Clone (8002) |
|---|---|---|---|
| CASA_LEVEL_FROM_ASSESSMENT_MODULE_VERSION | Niveau évalué figé par la version de module de l'évaluation ; publication refusée sans module_version valide | non défini, donc désactivé | 1 (phases 1-2), puis 0 (phase 3) |
| CASA_EXTRA_ATTEMPT_GRANTS | Octroi d'une tentative supplémentaire ; API /api/admin/attempt-grants | non défini, donc désactivé | 1 (phases 1-2), puis 0 (phase 3) |

Preuve, interrupteurs désactivés :
- **Échantillon de 23 réponses d'API en lecture seule** (anonyme, apprenant démo, admin) :
  - catalogue, modules, évaluations, parcours, vérification ;
  - tableau de bord, certifications, acquis, progression ;
  - liste des certificats et des utilisateurs, /admin/attempt-grants.
  
  Les SHA-256 sont identiques avant le code, après le code et après le test.
- **Empreinte de test_database**, avant le code puis après le test : seules ont changé les collections touchées par les brouillons de contenu, qui sont autorisés :
  - questions +1 (Q-M01-G1 v2) ;
  - assessment_versions +1 (A-M01-G v2) ;
  - resource_versions (révision de A-002 v2) ;
  - catalog_change_log +19.
  
  Users, attempts, attainments, awards, enrollments, module_completions et resource_progress sont inchangés.
- **Pendant le test isolé**, test_database est identique avant et après : 1268 documents, toutes les empreintes égales.

## 2. Règle du niveau évalué — option (ii)

- **Lien figé** : chaque version d'évaluation porte module_id et module_version, renseignés dans le brouillon. À la publication, module_version est obligatoire et la version de module doit exister. Une version publiée est immuable.
- **À chaque tentative** sont enregistrés assessment_version, module_version et level_evaluated, c'est-à-dire le niveau maximal de cette version de module.
- **L'acquis** reprend level_evaluated, enregistré aussi dans sa preuve (evidence.module_version et evidence.level_evaluated). Publier un module plus avancé ne relève jamais le niveau rétroactivement. Aucun recalcul.

**Règle de repli pour les versions déjà publiées sans module_version** : aucune écriture en base. La version de module retenue est la dernière version publiée du même module dont la date de publication est antérieure ou égale à celle de la version d'évaluation. À défaut, c'est la première version publiée du module.
- Cette règle est déterministe et figée : les dates de publication passées ne changent jamais.
- Aujourd'hui, toutes les versions publiées datent du 2026-09-01. Le repli donne donc M01 v1, M-001 v1 et M-003 v1.

**Migration proposée, à valider et non exécutée** : écrire module_version dans les 38 versions d'évaluation publiées, selon la règle de repli, pour qu'elle n'ait plus à être calculée. Cela suppose une dérogation écrite à l'immuabilité, sur ce seul champ. Rien n'est fait sans accord.

## 3. Tentative supplémentaire

- **Action admin** : POST /api/admin/attempt-grants (email, évaluation notée, motif d'au moins 3 caractères). Elle est enregistrée dans la collection attempt_grants avec les champs user_id, user_email, assessment_id, reason, granted_by, granted_at, consumed_at et attempt_id, et journalisée (action grant).
- **Effet** : +1 au maximum autorisé, pour ce couple apprenant–évaluation uniquement. Chaque octroi est consommé par une seule tentative. Les tentatives précédentes sont conservées : pas de remise à zéro, pas de réussite automatique.
- **Refus** :
  - apprenant ayant déjà réussi (409) ;
  - octroi déjà actif (409) ;
  - compte qui n'est pas un apprenant actif, y compris l'admin lui-même (400) ;
  - motif vide (422).
- **Affichage côté apprenant** : « 1 tentative supplémentaire accordée par l'administrateur ».

## 4. Test isolé — clone casa_e2e_plan

Préparation :
- Copie par mongodump puis mongorestore : 1268 documents et 59 index, identiques à la source.
- Seeds au démarrage : aucune écriture.
- Instance 127.0.0.1:8002 avec un secret propre (jwt_secret_plan, droits 600, jamais affiché) et le stockage coupé.
- Frontend de test sur le port 3101.
- Garde-fou : avant chaque écriture, DB_NAME et le port sont vérifiés via /proc.
- Comptes créés : uniquement qa-e2e-plan-* dans le clone.

| Scénario | Statut | Preuves |
|---|---|---|
| (g) A-M-003-G v2 publié trop tôt | RÉUSSI | 422 : questions v2 non publiées et « Certification rendue impossible — CERT-DOC-01 règle r1 » |
| (g) Évaluation sans module_version | RÉUSSI | 422 « Version de module évaluée (module_version) manquante ou inexistante » (élément de test A-E2E-NOMV) |
| Publication des éléments dans l'ordre de l'export | RÉUSSI | 20 éléments publiés (200). Seul A-E2E-NOMV est refusé, comme prévu |
| (a) Ancien inscrit P-001 v1, M-001 v1 terminé avant publication | RÉUSSI | Parcours resté en v1 (CO-001 v1 → M-001 v1). Libellé « Terminé (version 1) · Nouvelle évaluation disponible » vérifié à l'écran (capture capture_a_module_v1.png). A-M-001-G v1 5/5 : module_version 2, level_evaluated L1, K-001 au niveau L1 |
| (b) 3 tentatives épuisées sur A-M-003-G v1 avant la v2 | RÉUSSI | 4e tentative refusée (403) ; octroi 200 et journalisé ; message affiché (capture capture_b_tentative_accordee.png). 4e tentative (v2) : 200, octroi consommé et relié à la tentative ; les 3 premières sont inchangées (empreinte). 5e : 403 « (3 + 1 accordée(s)) ». Second octroi : 5e réussie. Octroi après réussite : 409. Total : 5 tentatives conservées |
| (c) Nouvel inscrit à P-001 v2, parcours complet | RÉUSSI | Inscription P-001 v2 ; K-001 L1 (M-001 v2) et K-003 L1 (M-003 v1) ; CERT-DOC-01 délivré (200). PDF : titulaire 200, admin 200, autre apprenant 404, visiteur 401 ; mention CLONE E2E et URL locale présentes ; /verify : valid. Après révocation : ancien code revoked ; réclamation 409 ; autorisation 200 ; nouvelle délivrance 200 ; après une 2e révocation : 409 |
| (d) A-M-003-G v2 seul | RÉUSSI | Seul K-003 est acquis, pas K-001 ; CERT-DOC-01 : 400 |
| (e) Non-rétroactivité | RÉUSSI | Une M-003 v2 de test en L1/L2 est publiée sur le clone. L'acquis obtenu avant (A-M-003-G v1, L1) reste L1. Un nouvel apprenant qui réussit A-M-003-G v2 après cette publication obtient level_evaluated L1 (M-003 v1) et K-003 en L1, pas L2 |
| (f) M01 | RÉUSSI | A-M01-G v2 publié. Les 25 tentatives copiées sont inchangées (empreinte). Un apprenant qui avait 2 tentatives v1 en a 2/3 en v2 ; sa 3e (v2) est enregistrée avec le niveau L0 (M01 v1) ; la 4e est refusée (403), les tentatives se cumulent |
| (h) Interrupteurs désactivés sur le clone | RÉUSSI | Tentative sans module_version ni level_evaluated ; acquis au niveau de la version publiée du module (L2, ancien comportement). /admin/attempt-grants : 404. L'octroi n'est plus pris en compte (3 tentatives maximum, 403). Publication sans module_version acceptée (200) |

## 5. Limites

- **Affichage « Niveau évalué : Lx (M-xxx vN) »** : vérifié par l'API et dans l'export. Côté apprenant, le libellé est prévu dans le résultat du quiz noté, mais il n'a pas été capturé à l'écran.
- **Colonne latérale du module** : elle affiche encore « 3/3 tentatives » quand une tentative supplémentaire est accordée. L'encadré du quiz, lui, indique correctement 3/4. C'est un écart d'affichage, derrière l'interrupteur.
- **Tentatives existantes** sans module_version : elles ne sont pas affichées avec un niveau évalué.
- **Scénario (h)** : la publication sans module_version a été acceptée sur le clone uniquement.
- **Mise en service** : la règle de repli et la migration éventuelle restent à valider avant toute activation en préproduction.
