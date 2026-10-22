# Rapport — correction du tableau de bord apprenant

Préproduction. Correction appliquée le 22/10/2026 (commit automatique cd63acd). Elle reste soumise à la validation du client.

## Cause

Le libellé du module était deviné en découpant l'identifiant du quiz au premier tiret. « A-M01-G » donne bien « M01 », mais « A-M-003-G » donne « M », qui n'existe pas : la page renvoyait alors une erreur 500.

## Diff exact

Fichier `backend/learning.py`, fonction `dashboard`, lignes 379 à 381.

Avant :

```
titles = {a: f"{mods[a.split('-')[1]]['code']} — {mods[a.split('-')[1]]['title']}" for a in {x['assessment_id'] for x in attempts}}
history = [{**{k: a[k] for k in [...]},
            "module_label": titles[a["assessment_id"]]} for a in reversed(attempts)]
```

Après :

```
titles = {x["module_id"]: f"{mods[x['module_id']]['code']} — {mods[x['module_id']]['title']}" for x in attempts if x["module_id"] in mods}
history = [{**{k: a[k] for k in [...]},
            "module_label": titles.get(a["module_id"], a["module_id"])} for a in reversed(attempts)]
```

La liste des champs `[...]` est identique avant et après. Le module vient désormais de la tentative elle-même (`module_id`, enregistré à chaque tentative).

## Reproduction : erreur 500 avant, 200 après

- Base isolée casa_e2e_revoc, apprenant qa-e2e-rev-a, qui a une tentative sur A-M-003-G.
- Même requête `GET /api/learners/me/dashboard`, sans aucune écriture :
  - **ancien code** (version précédant cd63acd) : **HTTP 500** ;
  - **nouveau code** : **HTTP 200**, libellé « M-003 — Fiabiliser une réponse documentaire ».
- L'empreinte de casa_e2e_revoc est identique avant et après.
- Constat d'origine : le 22/10 vers 12:14, sur l'instance isolée, l'erreur était `KeyError: 'M'`, avec un échec du chargement de l'espace apprenant dans le navigateur.

## Tentatives existantes de test_database

Comparaison en lecture seule entre l'ancien et le nouveau calcul du libellé :

| | Valeur |
|---|---|
| Tentatives | 37 |
| Évaluations | A-M01-G, A-M03-G, A-M09-G, A-M14-G |
| Libellés identiques | 37 |
| Libellés différents | 0 |

L'empreinte de test_database est inchangée.

## Annulation

```
cd /app && git show cd63acd -- backend/learning.py | git apply -R
```

Cette commande n'annule que ces lignes. À l'inverse, `git revert cd63acd` annulerait aussi les autres modifications de ce commit.

## Risques

- **Garder la correction** : aucun changement pour les 37 tentatives existantes. Une tentative dont le module n'est plus publié affiche l'identifiant du module au lieu de faire planter la page.
- **Annuler la correction** : le tableau de bord renverrait de nouveau l'erreur 500 pour tout apprenant ayant tenté A-M-003-G (possible dès aujourd'hui) ou A-M-001-G (une fois publiée), ou tout autre quiz dont le module porte un tiret.
