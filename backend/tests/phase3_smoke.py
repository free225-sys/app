import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from conftest import refuse_if_preprod
refuse_if_preprod("phase3_smoke.py")
import os
import random
import requests
from pymongo import MongoClient
from dotenv import load_dotenv
from creds import ADMIN

load_dotenv("/app/backend/.env")
API = "http://localhost:8001/api"
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def correct(mid):
    return {q["question_id"]: q["correct"] for q in mdb.questions.find({"module_id": mid, "question_id": {"$regex": f"^Q-{mid}-G"}})}


def complete_module(h, mid):
    for r in mdb.module_versions.find_one({"entity_id": mid})["resource_ids"]:
        requests.post(f"{API}/learners/me/resources/{r}/complete", headers=h)
    return requests.post(f"{API}/assessments/A-{mid}-G/attempts", headers=h, json={"answers": correct(mid)}).json()["module_progress"]["status"]


email = f"p3_{random.randint(1, 10**6)}@ex.ci"
tok = requests.post(f"{API}/auth/register", json={"first_name": "Awa", "last_name": "Traoré", "email": email, "password": "Motdepasse1"}).json()["access_token"]
h = {"Authorization": f"Bearer {tok}"}
print("enroll P01", requests.post(f"{API}/pathways/P01/enroll", headers=h).json()["percent"])
print("M09", complete_module(h, "M09"), "M14", complete_module(h, "M14"))
p2 = requests.post(f"{API}/pathways/P02/enroll", headers=h).json()
m09 = [m for c in p2["groups"]["mandatory"] for m in c["modules"] if m["module_id"] == "M09"][0]
print("P02 M09 recognized:", m09["recognized"], m09.get("recognition"), p2["recognized_counts"], [(t["competency_id"], t["status"], t["recognized"]) for t in p2["targets"]])
r = requests.post(f"{API}/credentials/CERT-CONC/claim", headers=h)
print("claim without project:", r.status_code, r.json())
sub = requests.post(f"{API}/projects/M16/submissions", headers=h, data={"title": "Assistant JO", "description": "x" * 80},
                    files={"file": ("projet.pdf", b"%PDF-1.4 test", "application/pdf")})
print("submit", sub.status_code, sub.json().get("status"), sub.json().get("file"))
sid = sub.json()["id"]
etok = requests.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}).json()["access_token"]
eh = {"Authorization": f"Bearer {etok}"}
print("pending", len(requests.get(f"{API}/evaluation/submissions?status=submitted", headers=eh).json()))
print("file", requests.get(f"{API}/projects/submissions/{sid}/file", headers=eh).content[:8])
rv = requests.post(f"{API}/evaluation/submissions/{sid}/review", headers=eh, json={"scores": {"cadrage": 3, "corpus": 2, "restitution": 3, "evaluation": 2, "gouvernance": 2}, "comment": "Projet solide et bien argumenté.", "decision": "validated"})
print("review", rv.status_code, rv.json().get("status"), rv.json().get("review", {}).get("percent"))
creds = requests.get(f"{API}/learners/me/credentials", headers=h).json()
print([(c["credential"]["id"], c["met_count"], c["total"], c["eligible"]) for c in creds])
award = requests.post(f"{API}/credentials/CERT-CONC/claim", headers=h).json()
print("award", award["code"], award["verification_url"])
pdf = requests.get(f"{API}/certificates/{award['code']}/pdf", headers=h)
print("pdf", pdf.status_code, pdf.headers.get("content-type"), len(pdf.content))
print("verify", requests.get(f"{API}/verify/{award['code']}").json()["status"])
atok = requests.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}).json()["access_token"]
ah = {"Authorization": f"Bearer {atok}"}
print("revoke", requests.post(f"{API}/admin/certificates/{award['code']}/revoke", headers=ah, json={"reason": "Test de révocation"}).json()["status"])
print("verify after", requests.get(f"{API}/verify/{award['code']}").json()["status"], requests.get(f"{API}/verify/CASA-XXXX-0000").json()["status"])
award2 = requests.post(f"{API}/credentials/CERT-CONC/claim", headers=h).json()
inv = requests.post(f"{API}/admin/attainments/{award2['evidence_refs'][2]['attainment_id']}/invalidate", headers=ah, json={"reason": "Plagiat"}).json()
print("invalidate", inv, requests.get(f"{API}/verify/{award2['code']}").json()["status"])
print("eligible after invalidation", [c["eligible"] for c in requests.get(f"{API}/learners/me/credentials", headers=h).json() if c["credential"]["id"] == "CERT-CONC"])
print("my pathways", [(p["pathway_id"], p["percent"]) for p in requests.get(f"{API}/learners/me/pathways", headers=h).json()])
