"""Read-only snapshot of public/learner-visible state for CERT-DOC-01 related entities."""
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
from creds import LEARNER  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
lt = requests.post(f"{API}/auth/login", json={"email": LEARNER[0], "password": LEARNER[1]}, timeout=15).json()["access_token"]
LH = {"Authorization": f"Bearer {lt}"}
g = lambda p, h=None: requests.get(f"{API}{p}", headers=h, timeout=20)  # noqa: E731
m = g("/modules/M-001").json()
out = {
    "module M-001": {"version": m.get("version"), "levels": m.get("levels")},
    "module M-001 assessments": [a["id"] for a in g("/modules/M-001/assessments").json()],
    "A-M-001-G public": g("/assessments/A-M-001-G").status_code,
    "A-M-001-G learner": g("/assessments/A-M-001-G", LH).status_code,
    "A-M-001-G learner attempts": g("/assessments/A-M-001-G/attempts", LH).status_code,
    "A-M-001-G attempt POST": requests.post(f"{API}/assessments/A-M-001-G/attempts", headers=LH, json={"answers": {}}, timeout=15).status_code,
    "CO-001": {k: g("/courses/CO-001").json().get(k) for k in ("version", "module_pins")},
    "CO-002": {k: g("/courses/CO-002").json().get(k) for k in ("version", "module_pins")},
    "learner module progress M-001": g("/learners/me/modules/M-001/progress", LH).json().get("graded") if g("/learners/me/modules/M-001/progress", LH).ok else g("/learners/me/modules/M-001/progress", LH).status_code,
    "counts": {c: db[c].count_documents({}) for c in ("attainments", "attempts", "awards", "enrollments", "module_completions", "resource_progress")},
    "entities": {"assessments A-M-001-G": db.assessments.count_documents({"_id": "A-M-001-G"}), "question_bank Q-M-001-G*": db.question_bank.count_documents({"_id": {"$regex": "^Q-M-001-G"}})},
    "published pointers": {e: db[c].find_one({"_id": e}, {"published_version": 1, "latest_version": 1}) for c, e in (("modules", "M-001"), ("courses", "CO-001"), ("courses", "CO-002"))},
}
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
