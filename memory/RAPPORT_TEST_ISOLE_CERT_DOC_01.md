# Rapport — tests isolés CERT-DOC-01 (casa_e2e et casa_e2e_revoc)

Préproduction. Aucun secret, jeton ni mot de passe ne figure dans ce rapport.

## Précautions communes

- **test_database (préproduction réelle)** : aucune écriture pendant les tests. Ses empreintes (nombres par collection et SHA-256 des documents) sont identiques avant et après : 38 collections, 1214 documents. Elles sont conservées dans /app/backups/e2e/fp_*.json.
- **Instance temporaire** : 127.0.0.1:8002, avec DB_NAME et CASA_TEST_DB pointant vers la base isolée.
  - Son JWT_SECRET est propre à l'instance, dans un fichier 600, jamais affiché.
  - Stockage objet coupé (STORAGE_DISABLED=1), aucun dépôt de fichier.
  - Certificats marqués « CLONE E2E — sans valeur », avec une URL de vérification locale.
- **Contrôle des écritures** : avant chaque écriture, les scripts vérifient DB_NAME et le port du processus (via /proc) et s'arrêtent si ce n'est pas la base isolée.
- **Seeds** : au démarrage de l'instance, ils n'ont rien écrit (empreintes inchangées).

## Test 1 — clone casa_e2e (21-22/10)

Préparation :
- Le clone a été créé par mongodump puis mongorestore. Nombres et index sont identiques à la source (38 collections, 1214 documents, 59 index).
- Le clone a été supprimé ensuite avec l'accord du client.

| Étape | Statut | Preuves |
|---|---|---|
| 1. Publication des 11 éléments | RÉUSSI | Contrôle réel : CO-001 v2 publié avant M-001 v2 → 422 « Module M-001 v2 non publié ». Puis 11 approbations (200) et 11 publications (200), dans l'ordre de l'export |
| 2. Réclamation sans condition | RÉUSSI | 400 « 0/3 preuves validées » ; conditions manquantes r1 (K-001 L1), r2 (K-003 L1), r3 (A-M-003-G réussi) |
| 3. Échec à 3/5 | RÉUSSI | 60 %, échouée ; K-001 à 5/8 = 62,5 %, non acquis ; M-001 en cours ; réclamation 400. Q3 cochée [a, b] au lieu de [a, b, c] → fausse (tout-ou-rien confirmé) |
| 4. Réussite à 4/5 puis 5/5 | RÉUSSI | 4/5 = 80 %, réussie ; K-001 à 75 %, niveau L1 ; M-001 v2 terminé ; réclamation 400 (1/3). Puis 5/5 : K-001 à 100 % |
| 5. Délivrance | RÉUSSI | 4e tentative → 403 « Nombre maximal de tentatives atteint (3) ». A-M-003-G 5/5 → K-003 L1 ; réclamation 200, certificat délivré |
| 6. PDF, vérification, révocation | RÉUSSI | PDF : titulaire 200, admin 200, autre apprenant 404, visiteur 401. Mention clone et URL locale présentes. /verify : valid. Révocation : revoked, PDF 410 |
| 7. Apprenants existants | RÉUSSI (API) | Données des comptes existants identiques à la préproduction. qa-e2e-C (M-001 v1 terminé avant publication) : M-001 v2 en cours, previous_completion = v1, 0 acquis, 0 certificat |
| 8. Nouvel inscrit à P-001 | RÉUSSI | Inscrit en P-001 v2 → CO-001 v2 → M-001 v2 |

Écarts trouvés :
- **CERT-DOC-01 était déjà obtenable sans M-001.** A-M-003-G portait K-001 (1 point sur chacune des questions G1, G3 et G5) au niveau L1. Un apprenant qui n'a fait que ce quiz avec 5/5 a obtenu le certificat. Correction préparée en brouillon : retrait de K-001 de ce quiz, avec un contrôle de publication.
- **Un certificat révoqué pouvait être immédiatement redemandé** : la réclamation suivante délivrait un nouveau certificat. Correction préparée : test 2.

Limites :
- L'affichage « Terminé (version 1) · Nouvelle évaluation disponible » n'a pas été vérifié à l'écran, car aucun frontend n'était relié au clone.
- Aucun compte existant n'avait terminé M-001 v1 : un compte de test a été utilisé.
- Le premier script s'est arrêté après l'étape 4 (erreur du script, sans effet sur les données). La reprise s'est faite depuis l'étape 5.

## Test 2 — base casa_e2e_revoc (22/10)

Préparation :
- La base a été créée vide puis remplie par les seeds de l'application. Elle ne contient aucune donnée réelle.
- Comptes utilisés : uniquement des comptes qa-e2e-, dont l'admin du clone, qui n'a aucun lien avec l'admin réel.
- La base est conservée à la demande du client.

| Test | Statut | Preuves |
|---|---|---|
| Révocation directe puis autorisation unique | RÉUSSI | 409 « Certificat révoqué : une nouvelle demande nécessite l'autorisation de l'administrateur ». Motif vide → 422 ; non-admin → 403 ; code inconnu → 404 ; doublon → 409. Autorisation journalisée (allow_reclaim), puis nouvelle délivrance 200. L'ancien certificat reste révoqué. Les champs de /verify sont inchangés |
| Consommation de l'autorisation | RÉUSSI | Consommée par la délivrance (issuance), puis par une nouvelle révocation (revocation). Réclamation suivante → 409 |
| Invalidation de preuve | RÉUSSI | Le certificat est révoqué automatiquement ; la réclamation renvoie 409 |
| Contrôle de publication (certifications) | RÉUSSI | A-M-003-G v2 sans K-001 → 422 « Certification rendue impossible — CERT-DOC-01 règle r1 ». Toujours 422 tant que M-001 reste en L0. Acceptée (200) après la publication de M-001 v2 (L1) |
| Interface apprenant | RÉUSSI | « Révoqué, nouvelle demande soumise à autorisation » s'affiche, sans bouton (frontend local relié à 8002) |
| Interface admin | RÉUSSI | « Autoriser une nouvelle demande » est désactivé sans motif. Après clic : « Nouvelle demande autorisée (valable une fois). » ; l'apprenant réclame ensuite → 200 |
| Tableau de bord apprenant | Écart corrigé | Erreur 500 pour une tentative sur A-M-003-G. Voir RAPPORT_CORRECTION_TABLEAU_DE_BORD.md |

Limites :
- Le test 2 a tourné sur une base vierge remplie par les seeds, pas sur une copie des données réelles.
- Le cas « autorisation consommée par une révocation » n'a été vérifié que pour une révocation postérieure à une nouvelle délivrance.
