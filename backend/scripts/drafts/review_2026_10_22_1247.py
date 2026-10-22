"""Client review 22/10 12:47: revise G1/G3/G4/G5 drafts through the circuit (return → edit → submit) and create harmonised drafts
A-002 v2, Q-M-001-F2 v2 and A-M-001-F v2. Nothing is approved or published."""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
from creds import ADMIN  # noqa: E402

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
tok = requests.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}, timeout=15).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}
META = {"_id", "id", "entity_id", "question_id", "version", "status", "approved", "changelog", "created_at", "created_by", "updated_at", "updated_by",
        "submitted_at", "submitted_by", "reviews", "published_at", "published_by", "superseded"}
RET = "Retours de relecture client (export du 22/10 12:47) : à corriger avant nouvelle soumission."
OLD_INF = "L'**inférence** est le calcul par lequel le modèle, à partir des tokens reçus, estime le token suivant le plus probable. Ce calcul mobilise les paramètres du modèle et des ressources matérielles (CPU ou GPU)."
NEW_INF = ("L'**inférence** est le calcul par lequel le modèle, à partir des tokens reçus, produit une distribution de probabilités sur le token suivant. "
           "Le token retenu est ensuite choisi selon les paramètres de génération, comme la température : ce n'est pas toujours le plus probable. "
           "Ce calcul mobilise les paramètres du modèle et des ressources matérielles (CPU ou GPU).")
A002_NOTE = "Citation A-002 alignée sur la version 2 de la ressource, en relecture (non publiée)."


def call(method, path, **kw):
    r = requests.request(method, f"{API}{path}", headers=H, timeout=30, **kw)
    assert r.status_code == 200, (method, path, r.status_code, r.text)
    return r.json()


def content(t, eid, v):
    d = call("GET", f"/admin/versions/{t}/{eid}/{v}")
    return {k: x for k, x in d.get("content", d).items() if k not in META}


def revise(t, eid, v, change, changelog):
    """Existing draft in review: return it, edit it in place, submit it again."""
    c = content(t, eid, v)
    change(c)
    call("POST", f"/admin/versions/{t}/{eid}/review", json={"decision": "return", "comment": RET})
    call("PUT", f"/admin/content/{t}/{eid}", json={"content": c, "changelog": changelog})
    call("POST", f"/admin/versions/{t}/{eid}/submit")
    print("révisé + resoumis", t, eid, f"v{v}")


def new_version(t, eid, base_v, change, changelog):
    c = content(t, eid, base_v)
    change(c)
    d = call("PUT", f"/admin/content/{t}/{eid}", json={"content": c, "changelog": changelog})
    call("POST", f"/admin/versions/{t}/{eid}/submit")
    print("nouveau brouillon + relecture", t, eid, f"v{d['latest']['version']}")
    return d["latest"]["version"]


def a002_quote(c):
    for s in c.get("sources") or []:
        if s.get("resource_id") == "A-002" and s.get("quote", "").startswith("L'**inférence**"):
            s["quote"] = NEW_INF
            c["source_note"] = (c.get("source_note") + " " if c.get("source_note") else "") + A002_NOTE


def g1(c):
    c["prompt"] = "Selon le schéma simplifié présenté dans M-001, dans quel ordre s'enchaînent les traitements qui produisent une réponse d'assistant ?"
    c["explanation"] = ("Dans le schéma simplifié de M-001, une réponse résulte d'une chaîne de traitements. La recherche, quand elle existe, précède l'inférence ; "
                        "les contrôles précèdent la restitution. Ce schéma est un modèle pédagogique simplifié : un système réel peut regrouper, répéter ou réorganiser certaines étapes.")


def g3(c):
    c["prompt"] = ("Une juriste utilise un assistant connecté à une API de modèle facturée à l'usage. Elle y colle l'intégralité d'un long recueil de textes. "
                   "L'assistant indique qu'il ne peut pas tout traiter en une fois, et le coût d'utilisation augmente nettement. Quelles explications sont correctes ? (plusieurs réponses)")
    next(o for o in c["options"] if o["id"] == "b")["text"] = "Avec cette API facturée à l'usage, le coût dépend du nombre de tokens traités"
    c["explanation"] = ("La mesure de la longueur d'un texte et la capacité de la fenêtre de contexte s'expriment en tokens, quel que soit l'assistant. "
                        "La facturation en tokens dépend en revanche du mode d'accès : elle s'applique ici parce que l'API est facturée à l'usage ; un autre mode d'accès, comme un abonnement, peut être facturé autrement.")


def g4(c):
    c["prompt"] = ("Cas d'application fictif : dans le cas CASA, l'assistant cite un « décret n° 2019-000 » — référence fictive, inventée pour cet exercice — qui n'existe pas dans la base documentaire. "
                   "Aucun extrait correspondant n'est affiché, alors que les extraits retrouvés étaient bien pertinents. Quelle étape a produit ce passage erroné ?")
    next(o for o in c["options"] if o["id"] == "b")["text"] = ("L'inférence et la génération : le modèle a produit, token par token, une formulation plausible à partir d'une distribution de probabilités, "
                                                               "sans s'appuyer sur un extrait retrouvé")
    c["explanation"] = ("La recherche retrouve des extraits existants ; elle ne rédige pas. Le texte est produit à l'inférence et à la génération : à chaque pas, le modèle calcule une distribution "
                        "de probabilités sur le token suivant, puis un token est choisi selon les paramètres de génération, comme la température, et pas forcément le plus probable. "
                        "Le modèle peut ainsi produire une formulation plausible, par exemple une référence, sans qu'elle soit vérifiée ni présente dans les sources. "
                        "C'est le rôle des contrôles de détecter qu'une citation n'est rattachée à aucun extrait.")
    a002_quote(c)


def g5(c):
    next(o for o in c["options"] if o["id"] == "c")["text"] = "Calculer, token après token, une distribution de probabilités sur la suite du texte"
    c["explanation"] = c["explanation"].replace("l'estimation du token suivant", "le calcul des probabilités du token suivant")
    a002_quote(c)


def a002(c):
    sec = next(s for s in c["sections"] if s["body"] == OLD_INF)
    sec["body"] = NEW_INF


def f2(c):
    c["prompt"] = "À quelle étape le modèle calcule-t-il la distribution de probabilités du token suivant ?"
    c["explanation"] = "L'inférence mobilise les paramètres du modèle pour calculer une distribution de probabilités sur le token suivant ; le token retenu dépend ensuite des paramètres de génération."


CL_Q = "Retours client du 22/10 12:47 : {} (brouillon, non publié)"
revise("question", "Q-M-001-G1", 1, g1, CL_Q.format("schéma simplifié de M-001 précisé dans l'énoncé et l'explication"))
revise("question", "Q-M-001-G3", 1, g3, CL_Q.format("contexte API facturée à l'usage, choix b et explication précisés ; bonnes réponses a, b, c et barème inchangés"))
revise("question", "Q-M-001-G4", 1, g4, CL_Q.format("cas d'application fictif, référence inventée, génération probabiliste corrigée (choix b, explication), citation A-002 v2"))
revise("question", "Q-M-001-G5", 1, g5, CL_Q.format("harmonisation de la génération probabiliste (choix c, explication), citation A-002 v2"))
new_version("resource", "A-002", 1, a002, CL_Q.format("harmonisation : l'inférence produit une distribution de probabilités, le choix dépend des paramètres de génération"))
f2v = new_version("question", "Q-M-001-F2", 1, f2, CL_Q.format("harmonisation de la formulation probabiliste (énoncé, explication) ; bonne réponse inchangée"))
new_version("assessment", "A-M-001-F", 1, lambda c: c.update(questions=[{**q, "version": f2v} if q["question_id"] == "Q-M-001-F2" else q for q in c["questions"]]),
            CL_Q.format(f"épinglage de Q-M-001-F2 v{f2v}"))
