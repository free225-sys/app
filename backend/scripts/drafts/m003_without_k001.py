"""Drafts: Q-M-003-G1/G3/G5 without K-001 and A-M-003-G v2 referencing them; submitted to review, never approved or published."""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
from creds import ADMIN  # noqa: E402

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
tok = requests.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}, timeout=15).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}
CL = "CERT-DOC-01 : retrait de K-001 du quiz noté de M-003 (K-003 inchangé ; brouillon, à valider par le client)"
META = ("version", "status", "approved", "changelog", "created_at", "created_by", "updated_at", "updated_by", "published_at", "published_by",
        "submitted_at", "submitted_by", "reviews", "entity_id", "_id", "superseded")


def call(method, path, **kw):
    r = requests.request(method, f"{API}{path}", headers=H, timeout=30, **kw)
    assert r.status_code == 200, (path, r.status_code, r.text)
    return r.json()


def new_version(t, eid, version, change):
    base = call("GET", f"/admin/versions/{t}/{eid}/{version}")
    base = base.get("content", base)
    content = {k: v for k, v in base.items() if k not in META}
    change(content)
    d = call("PUT", f"/admin/content/{t}/{eid}", json={"content": content, "changelog": CL})
    call("POST", f"/admin/versions/{t}/{eid}/submit")
    print("brouillon + relecture", t, eid, f"v{d['latest']['version']}")
    return d["latest"]["version"]


new = {}
for qid in ("Q-M-003-G1", "Q-M-003-G3", "Q-M-003-G5"):
    new[qid] = new_version("question", qid, 1, lambda c: c.update(competencies=[w for w in c["competencies"] if w["competency_id"] != "K-001"]))
new_version("assessment", "A-M-003-G", 1,
            lambda c: c.update(questions=[{"question_id": q["question_id"], "version": new.get(q["question_id"], q["version"])} for q in c["questions"]]))
