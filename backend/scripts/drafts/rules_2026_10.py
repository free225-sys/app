"""Client decisions (22/10, rules 2026-10): module_version on assessment drafts, A-002 v2 cost nuance with Q3 citations,
Q-M01-G1 v2 wording and A-M01-G v2. Drafts only, submitted to review; nothing approved or published."""
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
RET = "Décisions client du 22/10 (règles 2026-10) : brouillon renvoyé pour révision."

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



COST_OLD = "- Les coûts et la fenêtre de contexte s'expriment aussi en tokens."
CTX = "La fenêtre de contexte s'exprime en tokens."
COST = "Le coût dépend du mode d'accès et de la tarification ; il est souvent calculé en tokens pour les API facturées à l'usage."
NOTE = "Citations A-002 alignées sur la version 2 de la ressource, version en relecture (non publiée)."
CL = "Décisions client du 22/10 (règles 2026-10) : {} (brouillon, non publié)"


def a002(c):
    sec = c["sections"][0]
    assert COST_OLD in sec["body"]
    sec["body"] = sec["body"].replace(COST_OLD, f"- {CTX}\n- {COST}")


def g3(c):
    srcs = [s for s in c["sources"] if s["quote"] != "Les coûts et la fenêtre de contexte s'expriment aussi en tokens."]
    c["sources"] = srcs + [{"resource_id": "A-002", "quote": CTX}, {"resource_id": "A-002", "quote": COST}]
    c["source_note"] = NOTE


def q_m01_g1(c):
    old = "Le modèle prédit séquentiellement les tokens les plus probables"
    assert c["explanation"].startswith(old)
    c["explanation"] = c["explanation"].replace(old, "Le modèle produit sa réponse token par token, à partir d'une distribution de probabilités ; le token retenu n'est pas toujours le plus probable", 1)


revise("resource", "A-002", 2, a002, CL.format("coût selon le mode d'accès et la tarification ; fenêtre de contexte en tokens"))
revise("question", "Q-M-001-G3", 1, g3, CL.format("citations A-002 v2 (fenêtre de contexte, coût selon le mode d'accès)"))
for aid, v, mv in (("A-M-001-G", 1, 2), ("A-M-003-G", 2, 1), ("A-M-001-F", 2, 2)):
    revise("assessment", aid, v, lambda c, mv=mv: c.update(module_version=mv), CL.format(f"version de module évaluée figée : module_version = {mv}"))
g1v = new_version("question", "Q-M01-G1", 1, q_m01_g1, CL.format("formulation probabiliste corrigée dans l'explication ; énoncé, choix et réponse inchangés"))
mv = call("GET", "/modules/M01")["version"]
new_version("assessment", "A-M01-G", 1, lambda c: c.update(module_version=mv, questions=[{**q, "version": g1v} if q["question_id"] == "Q-M01-G1" else q for q in c["questions"]]),
            CL.format(f"épinglage de Q-M01-G1 v{g1v}, module_version = {mv}"))
print("M01 version publiée utilisée :", mv)
