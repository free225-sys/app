"""Add exact A-001/A-002 sources to Q-M-001-G1..G4 drafts (in-place revision) and create P-001/P-002 v2 drafts; submit to review. No approval, no publication."""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
from creds import ADMIN  # noqa: E402

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
tok = requests.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}, timeout=15).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}
CHAIN = "Une réponse d'assistant résulte d'une **chaîne de traitements** : interface, préparation, recherche éventuelle, inférence, génération, contrôles et restitution."
SOURCES = {
    "Q-M-001-G1": [("A-001", CHAIN)],
    "Q-M-001-G2": [("A-001", "Ouvrez la **démonstration interactive** et suivez la question « Quels textes régissent la commercialisation du café et du cacao ? » sur les sept étapes."),
                   ("A-001", "Repérez l'étape où intervient la recherche documentaire."), ("A-001", CHAIN)],
    "Q-M-001-G3": [("A-002", "Le modèle ne lit pas des mots mais des **tokens**, c'est-à-dire des fragments de texte. « commercialisation » peut ainsi être découpé en plusieurs morceaux."),
                   ("A-002", "La longueur d'un texte se mesure en tokens."), ("A-002", "Les coûts et la fenêtre de contexte s'expriment aussi en tokens.")],
    "Q-M-001-G4": [("A-001", "Identifiez l'étape où le modèle produit le texte."),
                   ("A-002", "L'**inférence** est le calcul par lequel le modèle, à partir des tokens reçus, estime le token suivant le plus probable. Ce calcul mobilise les paramètres du modèle et des ressources matérielles (CPU ou GPU).")],
}
CL_P = "CERT-DOC-01 option B : épinglage des cours v2 (brouillon, non publié)"


def call(method, path, **kw):
    r = requests.request(method, f"{API}{path}", headers=H, timeout=30, **kw)
    assert r.status_code == 200, (path, r.status_code, r.text)
    return r.json()


for qid, src in SOURCES.items():
    call("POST", f"/admin/versions/question/{qid}/review", json={"decision": "return", "comment": "Ajout des sources (passages exacts d'A-001/A-002) pour la relecture client ; contenu inchangé."})
    content = call("GET", f"/admin/versions/question/{qid}/1")["content"]
    content["sources"] = [{"resource_id": r, "quote": q} for r, q in src]
    call("PUT", f"/admin/content/question/{qid}", json={"content": content, "changelog": "Ajout des sources (A-001/A-002), énoncé, choix, réponses et explication inchangés"})
    d = call("POST", f"/admin/versions/question/{qid}/submit")
    print("sources added + review", qid, f"v{d['latest']['version']}")

for pid, courses in (("P-001", {"CO-001": 2}), ("P-002", {"CO-001": 2, "CO-002": 2})):
    content = call("GET", f"/admin/versions/pathway/{pid}/1")["content"]
    content["pathway_courses"] = [{**pc, "course_version": courses.get(pc["course_id"], pc["course_version"])} for pc in content["pathway_courses"]]
    d = call("PUT", f"/admin/content/pathway/{pid}", json={"content": content, "changelog": CL_P})
    call("POST", f"/admin/versions/pathway/{pid}/submit")
    print("draft+review pathway", pid, f"v{d['latest']['version']}", content["pathway_courses"])
