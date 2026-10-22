"""Blocage après révocation — runs ONLY against the isolated instance 127.0.0.1:8002 (CASA_TEST_DB=casa_e2e*)."""
import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
DBN = os.environ.get("CASA_TEST_DB", "")
BASE = "http://127.0.0.1:8002/api"
D = Path("/app/backups/e2e")
MSG = "Certificat révoqué : une nouvelle demande nécessite l'autorisation de l'administrateur"


def guard():
    pid = (D / "8002.pid").read_text().strip()
    env = dict(x.split("=", 1) for x in Path(f"/proc/{pid}/environ").read_bytes().decode().split("\0") if "=" in x)
    assert DBN.startswith("casa_e2e") and env.get("DB_NAME") == DBN == env.get("CASA_TEST_DB"), "cible non isolée"


@pytest.fixture(scope="module")
def db():
    guard()
    return MongoClient(os.environ["MONGO_URL"])[DBN]


def call(method, path, tok=None, body=None):
    if method != "GET":
        guard()
    r = requests.request(method, BASE + path, json=body, headers={"Authorization": f"Bearer {tok}"} if tok else {}, timeout=30)
    return r.status_code, (r.json() if "json" in r.headers.get("content-type", "") else r.content)


@pytest.fixture(scope="module")
def admin():
    st, d = call("POST", "/auth/login", body={"email": "qa-e2e-admin@example.com", "password": (D / "admin_password").read_text().strip()})
    assert st == 200
    return d["access_token"]


def learner(tag):
    st, d = call("POST", "/auth/register", body={"first_name": "QA", "last_name": f"E2E {tag}", "email": f"qa-e2e-{tag}@example.com", "password": "QaE2e-" + os.urandom(6).hex()})
    assert st == 200, d
    return d["access_token"], d["user"]["id"]


def earn(db, tok):
    v = db.assessment_versions.find_one({"entity_id": "A-M-003-G", "status": "published"}, sort=[("version", -1)])
    ans = {q["question_id"]: db.questions.find_one({"_id": f"{q['question_id']}@{q['version']}"})["correct"] for q in v["questions"]}
    st, r = call("POST", "/assessments/A-M-003-G/attempts", tok, {"answers": ans})
    assert st == 200 and r["attempt"]["passed"]


def cred_state(tok):
    _, lst = call("GET", "/learners/me/credentials", tok)
    return next(c for c in lst if c["credential"]["id"] == "CERT-DOC-01")


def test_direct_revocation_blocks_then_single_authorization(db, admin):
    tok, uid = learner("rev-a")
    earn(db, tok)
    st, a1 = call("POST", "/credentials/CERT-DOC-01/claim", tok)
    assert st == 200 and a1["status"] == "valid"
    _, v_before = call("GET", f"/verify/{a1['code']}")
    assert call("POST", f"/admin/certificates/{a1['code']}/revoke", admin, {"reason": "QA E2E révocation directe"})[0] == 200
    st, d = call("POST", "/credentials/CERT-DOC-01/claim", tok)
    assert st == 409 and d["detail"] == MSG
    assert cred_state(tok)["reclaim"] == {"blocked": True, "authorized": False}
    _, v = call("GET", f"/verify/{a1['code']}")
    assert v["status"] == "revoked" and set(v) == set(v_before)
    # authorization: reason mandatory, admin only, once
    assert call("POST", f"/admin/certificates/{a1['code']}/allow-reclaim", admin, {"reason": ""})[0] == 422
    assert call("POST", f"/admin/certificates/{a1['code']}/allow-reclaim", tok, {"reason": "pas admin"})[0] == 403
    assert call("POST", "/admin/certificates/CASA-XXXX-XXXX/allow-reclaim", admin, {"reason": "inconnu"})[0] == 404
    st, d = call("POST", f"/admin/certificates/{a1['code']}/allow-reclaim", admin, {"reason": "QA E2E autorisation après vérification"})
    assert st == 200 and d["reclaim"]["authorized"] is True
    assert call("POST", f"/admin/certificates/{a1['code']}/allow-reclaim", admin, {"reason": "QA E2E doublon"})[0] == 409
    assert db.catalog_change_log.find_one({"entity_id": a1["code"], "action": "allow_reclaim", "details": "QA E2E autorisation après vérification"})
    assert cred_state(tok)["reclaim"] == {"blocked": False, "authorized": True}
    st, a2 = call("POST", "/credentials/CERT-DOC-01/claim", tok)
    assert st == 200 and a2["status"] == "valid" and a2["code"] != a1["code"]
    assert db.reclaim_authorizations.find_one({"user_id": uid, "status": "consumed", "consumed_by": "issuance", "consumed_code": a2["code"]})
    assert call("GET", f"/verify/{a1['code']}")[1]["status"] == "revoked"
    assert call("POST", f"/admin/certificates/{a2['code']}/allow-reclaim", admin, {"reason": "QA E2E certificat valide"})[0] == 409
    # new revocation: blocked again, authorization already consumed
    assert call("POST", f"/admin/certificates/{a2['code']}/revoke", admin, {"reason": "QA E2E seconde révocation"})[0] == 200
    st, d = call("POST", "/credentials/CERT-DOC-01/claim", tok)
    assert st == 409 and d["detail"] == MSG
    _, lst = call("GET", "/admin/certificates", admin)
    rows = {a["code"]: a["reclaim"] for a in lst}
    assert rows[a2["code"]]["can_authorize"] is True and rows[a1["code"]]["can_authorize"] is False


def test_authorization_consumed_by_new_revocation(db, admin):
    tok, uid = learner("rev-c")
    earn(db, tok)
    _, a1 = call("POST", "/credentials/CERT-DOC-01/claim", tok)
    call("POST", f"/admin/certificates/{a1['code']}/revoke", admin, {"reason": "QA E2E révocation"})
    assert call("POST", f"/admin/certificates/{a1['code']}/allow-reclaim", admin, {"reason": "QA E2E autorisation"})[0] == 200
    _, a2 = call("POST", "/credentials/CERT-DOC-01/claim", tok)
    assert call("POST", f"/admin/certificates/{a2['code']}/revoke", admin, {"reason": "QA E2E révocation 2"})[0] == 200
    assert db.reclaim_authorizations.count_documents({"user_id": uid, "status": "active"}) == 0
    assert call("POST", "/credentials/CERT-DOC-01/claim", tok)[0] == 409


def test_evidence_invalidation_blocks(db, admin):
    tok, uid = learner("rev-b")
    earn(db, tok)
    st, a1 = call("POST", "/credentials/CERT-DOC-01/claim", tok)
    assert st == 200
    att = next(e["attainment_id"] for e in a1["evidence_refs"] if e.get("attainment_id"))
    st, d = call("POST", f"/admin/attainments/{att}/invalidate", admin, {"reason": "QA E2E invalidation de preuve"})
    assert st == 200 and a1["code"] in d["revoked_certificates"]
    db_att = db.attainments.find_one({"user_id": uid, "status": "valid"})
    assert db_att is not None
    st, d = call("POST", "/credentials/CERT-DOC-01/claim", tok)
    assert st == 409 and d["detail"] == MSG
    assert cred_state(tok)["reclaim"]["blocked"] is True
    assert call("GET", f"/verify/{a1['code']}")[1]["status"] == "revoked"
