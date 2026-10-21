import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from conftest import refuse_if_preprod
refuse_if_preprod("phase4_smoke.py")
import os
import uuid

import requests
from creds import ADMIN

API = os.environ.get("API_URL", "http://localhost:8001") + "/api"


def login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


AD = login(*ADMIN)
A = R = LD = AD

print("author users:", requests.get(f"{API}/admin/users", headers=A).status_code)
print("admin users:", requests.get(f"{API}/admin/users", headers=AD).status_code)

sfx = uuid.uuid4().hex[:5]
cid = f"concept-pd01-{sfx}"
content = {"name": f"Notion PD01 {sfx}", "short": "Définition courte.", "definition": "Définition complète.", "example": "Exemple.",
           "treatment": {"L0": "a"}, "stage_ids": ["stage-01", "stage-04"], "layer_ids": ["layer-application", "layer-donnees", "layer-modeles"],
           "prerequisite_ids": ["concept-prompt"], "module_ids": ["M02"]}
r = requests.post(f"{API}/admin/content/concept", headers=A, json={"id": cid, "content": content})
print("create concept:", r.status_code, r.json().get("latest", {}).get("status"))
print("submit:", requests.post(f"{API}/admin/versions/concept/{cid}/submit", headers=A).status_code)
print("author publish (403):", requests.post(f"{API}/admin/versions/concept/{cid}/publish", headers=A).status_code)
print("return:", requests.post(f"{API}/admin/versions/concept/{cid}/review", headers=R, json={"decision": "return", "comment": "Préciser l'exemple"}).json()["latest"]["status"])
content["example"] = "Exemple précisé."
print("save draft:", requests.put(f"{API}/admin/content/concept/{cid}", headers=A, json={"content": content}).json()["latest"]["version"])
requests.post(f"{API}/admin/versions/concept/{cid}/submit", headers=A)
print("approve:", requests.post(f"{API}/admin/versions/concept/{cid}/review", headers=R, json={"decision": "approve"}).json()["latest"]["approved"])
print("publish:", requests.post(f"{API}/admin/versions/concept/{cid}/publish", headers=LD).status_code)
pub = [c for c in requests.get(f"{API}/concepts").json() if c["id"] == cid]
print("public count:", len(pub))

r = requests.get(f"{API}/admin/content/module/M09", headers=A).json()
mc = r["latest"]["content"]
mc["summary"] = mc["summary"] + " (révisé)"
r = requests.put(f"{API}/admin/content/module/M09", headers=A, json={"content": mc, "changelog": "Révision résumé"})
print("M09 edit ->", r.json()["latest"]["version"], r.json()["latest"]["status"])
print("edit published v1:", requests.put(f"{API}/admin/versions/module/M09/1", headers=A, json={"content": mc}).status_code)
c03 = requests.get(f"{API}/courses/C03").json()
print("C03 M09 pinned:", [m["pinned_version"] for m in c03["modules"] if m["id"] == "M09"])

cyc = f"concept-cyc-{sfx}"
cc = dict(content, name=f"Cycle {sfx}", prerequisite_ids=[cid])
requests.post(f"{API}/admin/content/concept", headers=A, json={"id": cyc, "content": cc})
for h, path in [(A, "submit"), (R, "review")]:
    requests.post(f"{API}/admin/versions/concept/{cyc}/{path}", headers=h, json={"decision": "approve"})
print("publish cyc:", requests.post(f"{API}/admin/versions/concept/{cyc}/publish", headers=LD).status_code)
content["prerequisite_ids"] = [cyc]
requests.put(f"{API}/admin/content/concept/{cid}", headers=A, json={"content": content})
requests.post(f"{API}/admin/versions/concept/{cid}/submit", headers=A)
requests.post(f"{API}/admin/versions/concept/{cid}/review", headers=R, json={"decision": "approve"})
r = requests.post(f"{API}/admin/versions/concept/{cid}/publish", headers=LD)
print("cycle publish:", r.status_code, r.json()["detail"])
print("log:", len(requests.get(f"{API}/admin/changelog", headers=A, params={"entity_id": cid}).json()))
requests.post(f"{API}/events", json={"type": "demo_layer_click", "layer_id": "layer-donnees", "step": 2})
print("analytics:", requests.get(f"{API}/admin/analytics", headers=LD).json()["demo"])
