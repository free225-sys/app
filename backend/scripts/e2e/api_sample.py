"""Read-only API sample: SHA-256 of GET responses (anonymous, demo learner, admin) to prove unchanged behaviour."""
import hashlib
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
import creds  # noqa: E402

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
ANON = ["/modules/M-001", "/modules/M-003", "/modules/M01", "/modules/M-001/assessments", "/modules/M-003/assessments", "/modules/M01/assessments",
        "/assessments/A-M-001-F", "/credentials", "/pathways/P-001", "/pathways/P-002", "/courses/CO-001", "/verify/CASA-6BGF-RDYM"]
LEARNER = ["/learners/me/dashboard", "/learners/me/credentials", "/learners/me/attainments", "/learners/me/modules/M-001/progress",
           "/learners/me/modules/M01/progress", "/assessments/A-M01-G", "/assessments/A-M-003-G", "/assessments/A-M01-G/attempts"]
ADMIN = ["/admin/certificates", "/admin/users", "/admin/attempt-grants"]


def token(email, pw):
    return requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15).json()["access_token"]


def sample(paths, tok=None):
    out = {}
    for p in paths:
        r = requests.get(API + p, headers={"Authorization": f"Bearer {tok}"} if tok else {}, timeout=30)
        out[p] = [r.status_code, hashlib.sha256(r.content).hexdigest()[:16]]
    return out


res = {"anonyme": sample(ANON), "apprenant démo": sample(LEARNER, token(*creds.LEARNER)), "admin": sample(ADMIN, token(*creds.ADMIN))}
Path(sys.argv[1]).write_text(json.dumps(res, ensure_ascii=False, indent=1))
print(sum(len(v) for v in res.values()), "réponses échantillonnées")
