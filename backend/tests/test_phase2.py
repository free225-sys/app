"""Backend tests for Phase 2 — Auth + Learning (CASA AI Academy)."""
import os
import uuid
import time
import pytest
from creds import ADMIN
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://relais-footer.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = ADMIN[0]
ADMIN_PASSWORD = ADMIN[1]


def _fresh_email():
    return f"TEST_{uuid.uuid4().hex[:10]}@example.com"


@pytest.fixture(scope="module")
def s():
    return requests.Session()


# ---------- openapi ----------
def test_openapi(s):
    r = s.get(f"{API}/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    for p in ["/api/auth/register", "/api/auth/login", "/api/auth/me", "/api/auth/logout",
              "/api/diagnostic", "/api/diagnostic/submit",
              "/api/modules/{module_id}/assessments",
              "/api/learners/me/modules/{module_id}/progress",
              "/api/learners/me/courses/{course_id}/progress",
              "/api/learners/me/dashboard", "/api/learners/me/attainments"]:
        assert p in paths, f"missing {p}"


# ---------- Register / Login / Me / Logout ----------
def test_register_login_me_logout():
    sess = requests.Session()
    email = _fresh_email()
    r = sess.post(f"{API}/auth/register", json={
        "first_name": "T", "last_name": "User", "email": email, "password": "Password1!"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data and data["user"]["email"] == email.lower()
    assert "learner" in data["user"]["roles"]
    token = data["access_token"]

    # /me using Bearer
    r2 = sess.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["email"] == email.lower()

    # duplicate -> 409
    rdup = requests.post(f"{API}/auth/register", json={
        "first_name": "T", "last_name": "U", "email": email, "password": "Password1!"})
    assert rdup.status_code == 409

    # password too short -> 422 (pydantic validation)
    rshort = requests.post(f"{API}/auth/register", json={
        "first_name": "T", "last_name": "U", "email": _fresh_email(), "password": "short"})
    assert rshort.status_code == 422

    # login works
    rl = requests.post(f"{API}/auth/login", json={"email": email, "password": "Password1!"})
    assert rl.status_code == 200

    # logout
    rout = requests.post(f"{API}/auth/logout")
    assert rout.status_code == 200


def test_forgot_password():
    r = requests.post(f"{API}/auth/forgot-password", json={"email": "x@y.z"})
    assert r.status_code == 200
    assert "administrateur" in r.json()["message"].lower()


def test_login_brute_force_lockout():
    email = _fresh_email()
    r = requests.post(f"{API}/auth/register", json={
        "first_name": "T", "last_name": "U", "email": email, "password": "Password1!"})
    assert r.status_code == 200
    # Spec: 5 wrong -> 429. Current impl ties ident to request.client.host (ingress IP) which varies
    # across pods behind the load balancer, so attempts are split and lockout triggers only after many tries.
    statuses = []
    for i in range(15):
        rr = requests.post(f"{API}/auth/login", json={"email": email, "password": "WRONG!!"})
        statuses.append(rr.status_code)
        if rr.status_code == 429:
            break
    assert 429 in statuses, f"brute-force lockout never triggered within 15 tries: {statuses}"
    # Spec compliance: should trigger by attempt 6; may fail due to the per-pod identifier bug
    first_429 = statuses.index(429) + 1
    assert first_429 <= 6, (
        f"Spec says 5 fails -> 429 (so by attempt 6). Got first 429 on attempt {first_429}. "
        "Likely cause: ident = f'{request.client.host}:{email}' varies across backend pods; "
        "login_attempts counters are fragmented. Use just email (or X-Forwarded-For) as ident.")


# ---------- Diagnostic ----------
def test_diagnostic_and_submit_anonymous():
    r = requests.get(f"{API}/diagnostic")
    assert r.status_code == 200
    d = r.json()
    assert len(d["questions"]) == 8
    # ensure no 'correct' leaked
    for q in d["questions"]:
        assert "correct" not in q
        assert "explanation" not in q
    # submit (empty answers)
    rs = requests.post(f"{API}/diagnostic/submit", json={"answers": {}})
    assert rs.status_code == 200
    res = rs.json()
    assert res["saved"] is False
    assert "profile_id" in res and "course_id" in res


# ---------- Assessments ----------
def test_module_assessments_M01():
    r = requests.get(f"{API}/modules/M01/assessments")
    assert r.status_code == 200
    data = r.json()
    kinds = {a["id"]: a for a in data}
    assert "A-M01-F" in kinds and "A-M01-G" in kinds


def test_graded_requires_auth_and_no_leaks():
    r = requests.get(f"{API}/assessments/A-M01-G")
    assert r.status_code == 401
    # with auth
    tok = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).json()["access_token"]
    r2 = requests.get(f"{API}/assessments/A-M01-G", headers={"Authorization": f"Bearer {tok}"})
    assert r2.status_code == 200
    for q in r2.json()["questions"]:
        assert "correct" not in q, q
        assert "explanation" not in q, q


def test_formative_check():
    r = requests.get(f"{API}/assessments/A-M01-F")
    assert r.status_code == 200
    first_q = r.json()["questions"][0]
    rc = requests.post(f"{API}/assessments/A-M01-F/check",
                       json={"question_id": first_q["question_id"], "answer": ["a"]})
    assert rc.status_code == 200
    body = rc.json()
    assert "correct" in body and "explanation" in body


# ---------- Full graded attempt flow (fresh user) ----------
@pytest.fixture(scope="module")
def fresh_user_token():
    email = _fresh_email()
    r = requests.post(f"{API}/auth/register", json={
        "first_name": "G", "last_name": "User", "email": email, "password": "Password1!"})
    assert r.status_code == 200
    return r.json()["access_token"], email


def _hdr(tok): return {"Authorization": f"Bearer {tok}"}


def test_graded_failing_then_passing_then_limit(fresh_user_token):
    tok, email = fresh_user_token
    # mark all 4 resources complete (M01)
    mod = requests.get(f"{API}/modules/M01").json()
    for res in mod["resources"]:
        rc = requests.post(f"{API}/learners/me/resources/{res['id']}/complete", headers=_hdr(tok))
        assert rc.status_code == 200
    prog = requests.get(f"{API}/learners/me/modules/M01/progress", headers=_hdr(tok)).json()
    assert prog["resources_done"] == len(mod["resources"])
    assert prog["status"] in ("in_progress", "not_started", "completed")
    # Attempt 1: wrong answers
    bad = {"Q-M01-G1": ["a"], "Q-M01-G2": ["b"], "Q-M01-G3": ["c"], "Q-M01-G4": ["a"], "Q-M01-G5": ["b"]}
    r1 = requests.post(f"{API}/assessments/A-M01-G/attempts", json={"answers": bad}, headers=_hdr(tok))
    assert r1.status_code == 200, r1.text
    assert r1.json()["attempt"]["passed"] is False
    # Attempt 2: correct answers
    good = {"Q-M01-G1": ["b"], "Q-M01-G2": ["a"], "Q-M01-G3": ["a", "b", "d"],
            "Q-M01-G4": ["b"], "Q-M01-G5": ["a"]}
    r2 = requests.post(f"{API}/assessments/A-M01-G/attempts", json={"answers": good}, headers=_hdr(tok))
    assert r2.status_code == 200
    assert r2.json()["attempt"]["passed"] is True
    assert r2.json()["module_progress"]["status"] == "completed"
    # per-competency populated
    comps = {c["competency_id"] for c in r2.json()["attempt"]["per_competency"]}
    assert len(comps) >= 2
    # Attempt 3: anything
    r3 = requests.post(f"{API}/assessments/A-M01-G/attempts", json={"answers": good}, headers=_hdr(tok))
    assert r3.status_code == 200
    # Attempt 4 -> 403
    r4 = requests.post(f"{API}/assessments/A-M01-G/attempts", json={"answers": good}, headers=_hdr(tok))
    assert r4.status_code == 403
    assert "max" in r4.json()["detail"].lower() or "tentatives" in r4.json()["detail"].lower()


def test_dashboard_and_attainments_and_course_progress(fresh_user_token):
    tok, _ = fresh_user_token
    # course progress C01
    rc = requests.get(f"{API}/learners/me/courses/C01/progress", headers=_hdr(tok))
    assert rc.status_code == 200
    cp = rc.json()
    assert cp["course_id"] == "C01"
    assert cp["percent"] > 0
    # M01 should be completed
    m01 = next((m for m in cp["modules"] if m["module_id"] == "M01"), None)
    assert m01 and m01["status"] == "completed"
    # dashboard
    rd = requests.get(f"{API}/learners/me/dashboard", headers=_hdr(tok))
    assert rd.status_code == 200
    dash = rd.json()
    assert any(a["assessment_id"] == "A-M01-G" for a in dash["attempts"])
    # attainments
    ra = requests.get(f"{API}/learners/me/attainments", headers=_hdr(tok))
    assert ra.status_code == 200
    atts = ra.json()
    assert len(atts) >= 1
    for a in atts:
        assert "level" in a and "evidence" in a


def test_demo_progress_attach():
    email = _fresh_email()
    tok = requests.post(f"{API}/auth/register", json={
        "first_name": "D", "last_name": "U", "email": email, "password": "Password1!"}).json()["access_token"]
    scenario = requests.get(f"{API}/demo/scenarios/casa-jo-cafe-cacao").json()
    quiz_answers = {q["id"]: q["correct"] for q in scenario["quiz"]}
    r = requests.post(f"{API}/learners/me/demo-progress",
                      json={"scenario_id": "casa-jo-cafe-cacao", "max_step": 7, "quiz_answers": quiz_answers},
                      headers=_hdr(tok))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["completed"] is True
    assert body["quiz_score"] == len(scenario["quiz"])
