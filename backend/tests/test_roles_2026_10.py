"""Acceptance tests — roles consolidation 2026-10 (single admin + learners). QA data is prefixed qa-role-/QA-ROLE- and cleaned up."""
import asyncio
import os
import re
import uuid

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from creds import ADMIN, LEARNER

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0] + "/api"
DB = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
SFX = uuid.uuid4().hex[:8]
H = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731


def login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def register(tag, **extra):
    email = f"qa-role-{tag}-{SFX}@example.com"
    r = requests.post(f"{API}/auth/register", json={"first_name": "QA-ROLE", "last_name": tag, "email": email, "password": "QaRole-Pass-1", **extra}, timeout=15)
    assert r.status_code == 200, r.text
    return email, r.json()["access_token"]


@pytest.fixture(scope="module")
def admin():
    return login(*ADMIN)


@pytest.fixture(scope="module")
def learner():
    return register("learner")


def test_single_admin_and_index():
    assert DB.users.count_documents({"role": "admin"}) == 1
    idx = DB.users.index_information()["unique_single_admin"]
    assert idx["unique"] and idx["partialFilterExpression"] == {"role": "admin"}
    assert DB.users.count_documents({"roles": {"$exists": True}}) == 0
    a = DB.users.find_one({"role": "admin"})
    assert a["email"] == "admin@casa-academy.com" and a["legacy_roles"] == ["admin", "learner"]


def test_concurrent_admin_insertions_isolated_db():
    name = os.environ["DB_NAME"] + "_qa_role_concurrency"

    async def run():
        db = AsyncIOMotorClient(os.environ["MONGO_URL"])[name]
        await db.users.drop()
        await db.users.create_index("email", unique=True)
        await db.users.create_index([("role", 1)], name="unique_single_admin", unique=True, partialFilterExpression={"role": "admin"})

        async def ins(i):
            try:
                await db.users.insert_one({"email": f"qa-role-c{i}@example.com", "role": "admin"})
                return True
            except DuplicateKeyError:
                return False
        res = await asyncio.gather(*[ins(i) for i in range(20)])
        n = await db.users.count_documents({"role": "admin"})
        await db.client.drop_database(name)
        return sum(res), n
    ok, n = asyncio.run(run())
    assert ok == 1 and n == 1


def test_concurrent_promotions_real_db_all_refused():
    ids = [DB.users.insert_one({"email": f"qa-role-p{i}-{SFX}@example.com", "first_name": "QA-ROLE", "last_name": "p", "role": "learner",
                                "session_version": 0, "active": True, "created_at": "2026-10-21"}).inserted_id for i in range(20)]

    async def run():
        db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

        async def promote(_id):
            try:
                await db.users.update_one({"_id": _id}, {"$set": {"role": "admin"}})
                return True
            except DuplicateKeyError:
                return False
        return await asyncio.gather(*[promote(i) for i in ids])
    assert sum(asyncio.run(run())) == 0
    assert DB.users.count_documents({"role": "admin"}) == 1


@pytest.mark.parametrize("extra", [{"role": "admin"}, {"roles": ["admin"]}, {"is_admin": True}, {"legacy_roles": ["admin"]},
                                   {"role": "admin", "roles": ["admin"], "is_admin": True, "legacy_roles": ["pedagogical_lead"], "session_version": 99}])
def test_register_manipulated_creates_learner(extra):
    email, tok = register("reg" + uuid.uuid4().hex[:4], **extra)
    d = DB.users.find_one({"email": email})
    assert d["role"] == "learner" and "is_admin" not in d and "legacy_roles" not in d and d["session_version"] == 0 and "roles" not in d
    assert requests.get(f"{API}/admin/content-types", headers=H(tok), timeout=15).status_code == 403


def test_admin_create_user_only_learner(admin):
    email = f"qa-role-created-{SFX}@example.com"
    r = requests.post(f"{API}/admin/users", headers=H(admin), json={"email": email, "first_name": "QA-ROLE", "last_name": "c", "password": "QaRole-Pass-1",
                                                                      "roles": ["admin"], "role": "admin"}, timeout=15)
    assert r.status_code == 200 and r.json()["roles"] == ["learner"]
    assert DB.users.find_one({"email": email})["role"] == "learner"


def _admin_routes():
    spec = requests.get(f"{API}/openapi.json", timeout=15).json()
    for path, ops in spec["paths"].items():
        if path.startswith("/api/admin") or path.startswith("/api/evaluation"):
            for m in ops:
                yield m.upper(), re.sub(r"\{[^}]+\}", "x", path)


def test_admin_and_evaluation_endpoints_refused(learner):
    routes = list(_admin_routes())
    assert len(routes) >= 25
    for method, path in routes:
        anon = requests.request(method, API.rsplit("/api", 1)[0] + path, json={}, timeout=15)
        lrn = requests.request(method, API.rsplit("/api", 1)[0] + path, headers=H(learner[1]), json={}, timeout=15)
        assert anon.status_code == 401, (method, path, anon.status_code)
        assert lrn.status_code == 403, (method, path, lrn.status_code)


def test_admin_cannot_write_learning_data(admin):
    before = {c: DB[c].count_documents({}) for c in ("enrollments", "attempts", "resource_progress", "demo_progress", "submissions", "diagnostic_results", "events")}
    calls = [("post", "/pathways/P01/enroll", {}), ("post", "/assessments/A-M01-G/attempts", {"answers": {}}), ("post", "/learners/me/resources/M01-R1/complete", {}),
             ("post", "/learners/me/demo-progress", {"max_step": 3, "quiz_answers": {}}), ("get", "/learners/me/dashboard", None), ("post", "/credentials/CERT-CONC/claim", {})]
    for m, p, body in calls:
        assert getattr(requests, m)(f"{API}{p}", headers=H(admin), json=body, timeout=15).status_code == 403, p
    r = requests.post(f"{API}/projects/M16/submissions", headers=H(admin), data={"title": "QA-ROLE admin", "description": "x" * 60}, timeout=15)
    assert r.status_code == 403
    assert requests.post(f"{API}/events", headers=H(admin), json={"type": "demo_start", "session_id": "qa-role"}, timeout=15).json()["recorded"] is False
    r = requests.post(f"{API}/diagnostic/submit", headers=H(admin), json={"answers": {}}, timeout=15)
    assert r.status_code == 200 and r.json()["saved"] is False
    after = {c: DB[c].count_documents({}) for c in before}
    assert before == after


def test_admin_protections(admin):
    aid = str(DB.users.find_one({"role": "admin"})["_id"])
    for body in ({"active": False}, {"password": "QaRole-Pass-1"}, {"roles": ["learner"]}, {"role": "learner"}):
        r = requests.patch(f"{API}/admin/users/{aid}", headers=H(admin), json=body, timeout=15)
        assert r.status_code in (200, 400)
    a = DB.users.find_one({"role": "admin"})
    assert str(a["_id"]) == aid and a.get("active", True) is True
    assert requests.delete(f"{API}/admin/users/{aid}", headers=H(admin), timeout=15).status_code in (404, 405)


def test_temp_password_bumps_session_and_logs_without_password(admin):
    email, tok = register("temp")
    uid = str(DB.users.find_one({"email": email})["_id"])
    r = requests.patch(f"{API}/admin/users/{uid}", headers=H(admin), json={"password": "QaRole-Temp-2"}, timeout=15)
    assert r.status_code == 200
    assert DB.users.find_one({"email": email})["session_version"] == 1
    assert requests.get(f"{API}/auth/me", headers=H(tok), timeout=15).status_code == 401
    log = DB.catalog_change_log.find_one({"entity_id": email, "action": "update"}, sort=[("at", -1)])
    assert "provisoire" in log["details"] and "QaRole-Temp-2" not in str(log)
    login(email, "QaRole-Temp-2")


def test_retired_staff_cannot_login_and_kept_history():
    for e in ("evaluator", "author", "reviewer", "lead"):
        d = DB.users.find_one({"email": f"{e}@casa-academy.ci"})
        assert d["role"] == "learner" and d["active"] is False and d["legacy_roles"] and d["session_version"] >= 1
    assert DB.catalog_change_log.count_documents({"user_email": {"$in": ["author@casa-academy.ci", "lead@casa-academy.ci", "reviewer@casa-academy.ci"]}}) == 98
    assert DB.submissions.count_documents({"review.evaluator_name": {"$exists": True}}) >= 4


def test_revoked_certificates_stay_revoked():
    assert DB.awards.count_documents({"status": "valid"}) == 0 and DB.awards.count_documents({"status": "revoked"}) == 6
    code = DB.awards.find_one({"status": "revoked"})["code"]
    assert requests.get(f"{API}/verify/{code}", timeout=15).json()["status"] == "revoked"


def test_private_data_refused_to_other_learner(learner):
    other = DB.awards.find_one({})
    assert requests.get(f"{API}/certificates/{other['code']}/pdf", headers=H(learner[1]), timeout=15).status_code in (403, 404)
    sub = DB.submissions.find_one({})
    assert requests.get(f"{API}/projects/submissions/{sub['_id']}/file", headers=H(learner[1]), timeout=15).status_code in (403, 404)
    r = requests.get(f"{API}/assessments/A-M01-G/attempts", headers=H(learner[1]), timeout=15)
    assert r.status_code == 200 and r.json() == []


def test_m16_submission_then_admin_review(admin, learner):
    r = requests.post(f"{API}/projects/M16/submissions", headers=H(learner[1]), data={"title": "QA-ROLE projet M16", "description": "Projet de test QA-ROLE " + "détail " * 10}, timeout=20)
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    rub = requests.get(f"{API}/projects/M16/rubric", timeout=15).json()
    top = max(lv["score"] for lv in rub["levels"])
    r = requests.post(f"{API}/evaluation/submissions/{sid}/review", headers=H(admin), json={"scores": {c["id"]: top for c in rub["criteria"]}, "comment": "QA-ROLE évaluation complète", "decision": "validated"}, timeout=15)
    assert r.status_code == 200, r.text
    mine = requests.get(f"{API}/learners/me/submissions", headers=H(learner[1]), timeout=15).json()
    assert any(s["id"] == sid and s["status"] == "validated" for s in mine)


def test_import_export_no_promotion_no_publication(admin):
    pub = {c: DB[c].count_documents({"status": "published"}) for c in ("concept_versions", "module_versions", "course_versions", "pathway_versions")}
    data = requests.get(f"{API}/admin/catalog/export", headers=H(admin), timeout=30).json()
    data.setdefault("users", [{"email": "qa-role-injected@example.com", "role": "admin"}])
    r = requests.post(f"{API}/admin/catalog/import", headers=H(admin), json=data, timeout=60)
    assert r.status_code == 200
    assert {c: DB[c].count_documents({"status": "published"}) for c in pub} == pub
    assert DB.users.count_documents({"role": "admin"}) == 1 and not DB.users.find_one({"email": "qa-role-injected@example.com"})


@pytest.mark.parametrize("field", [{"role": "admin"}, {"roles": ["admin"]}, {"is_admin": True}, {"legacy_roles": ["admin"]}, {"session_version": 0}, {"is_active": True}, {"email": "x@y.z"}])
def test_patch_user_rejects_privileged_or_unknown_fields(admin, field):
    email, _ = register("patch" + uuid.uuid4().hex[:4])
    d0 = DB.users.find_one({"email": email})
    r = requests.patch(f"{API}/admin/users/{d0['_id']}", headers=H(admin), json={"first_name": "QA-ROLE-x", **field}, timeout=15)
    assert r.status_code == 400 and "Champ non autorisé" in r.json()["detail"] and next(iter(field)) in r.json()["detail"]
    d1 = DB.users.find_one({"email": email})
    assert {k: d1.get(k) for k in ("role", "first_name", "session_version", "active")} == {k: d0.get(k) for k in ("role", "first_name", "session_version", "active")}
    assert requests.patch(f"{API}/admin/users/{d0['_id']}", json={"role": "admin"}, timeout=15).status_code == 401


def _pass_graded(tok, aid):
    a = DB.assessments.find_one({"_id": aid})
    v = DB.assessment_versions.find_one({"entity_id": aid, "version": a["published_version"]})
    answers = {}
    for q in v["questions"]:
        qd = DB.questions.find_one({"question_id": q["question_id"], "version": q["version"]})
        answers[q["question_id"]] = qd["correct"]
    r = requests.post(f"{API}/assessments/{aid}/attempts", headers=H(tok), json={"answers": answers}, timeout=15)
    assert r.status_code == 200 and r.json()["attempt"]["passed"], r.text


def test_certificate_pdf_ownership(admin):
    a_email, a_tok = register("cert-a")
    b_email, b_tok = register("cert-b")
    for aid in ("A-M01-G", "A-M02-G", "A-M03-G"):
        _pass_graded(b_tok, aid)
    r = requests.post(f"{API}/credentials/CERT-FOND/claim", headers=H(b_tok), timeout=15)
    assert r.status_code == 200 and r.json()["status"] == "valid", r.text
    code = r.json()["code"]
    pdf = lambda t: requests.get(f"{API}/certificates/{code}/pdf", headers=H(t), timeout=30)  # noqa: E731
    assert pdf(a_tok).status_code in (403, 404)
    rb, ra = pdf(b_tok), pdf(admin)
    assert rb.status_code == 200 and rb.content[:4] == b"%PDF" and ra.status_code == 200 and ra.content[:4] == b"%PDF"
    assert requests.get(f"{API}/certificates/{code}/pdf", timeout=15).status_code == 401
    removed = DB.awards.delete_many({"code": code, "user_id": str(DB.users.find_one({"email": b_email})["_id"])}).deleted_count
    print("QA-ROLE test certificate deleted:", code, removed)
    assert DB.awards.count_documents({"status": "valid"}) == 0


def test_zz_cleanup_qa_role():
    users = list(DB.users.find({"email": {"$regex": "^qa-role-"}}, {"email": 1}))
    print("QA-ROLE accounts:", sorted(u["email"] for u in users))
    ids = [str(u["_id"]) for u in users]
    for c in ("submissions", "attainments", "attempts", "resource_progress", "module_completions", "enrollments", "demo_progress", "diagnostic_results", "awards"):
        DB[c].delete_many({"user_id": {"$in": ids}})
    DB.catalog_change_log.delete_many({"entity_id": {"$regex": "^qa-role-"}})
    DB.login_attempts.delete_many({"identifier": {"$regex": "^qa-role-"}})
    DB.users.delete_many({"email": {"$regex": "^qa-role-"}})
    print("QA-ROLE cleaned:", len(users), "accounts")
    assert DB.users.count_documents({"email": {"$regex": "^qa-role-"}}) == 0
