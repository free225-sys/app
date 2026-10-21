"""Phase 4 back-office — RBAC, workflow, versioning, change log, analytics,
and attainments de-duplication.  Also covers Phase 1-3 regression smoke."""
import os
import time
import uuid
from typing import Dict

import pytest
from creds import ADMIN, LEARNER
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://relais-footer.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

CREDS = {
    "admin": ADMIN, "learner": LEARNER, "author": ADMIN, "reviewer": ADMIN, "lead": ADMIN, "evaluator": ADMIN,
}

SFX = uuid.uuid4().hex[:6]


def _login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, f"login {email} failed → {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def tokens() -> Dict[str, str]:
    out = {}
    for key, (email, pw) in CREDS.items():
        out[key] = _login(email, pw)
    return out


def H(tok): return {"Authorization": f"Bearer {tok}"}


# ---------- 1. Attainments dedupe ----------
class TestAttainmentsDedup:
    def test_no_duplicates(self, tokens):
        r = requests.get(f"{API}/learners/me/attainments", headers=H(tokens["learner"]), timeout=15)
        assert r.status_code == 200
        atts = r.json()
        assert isinstance(atts, list)
        keys = [(a.get("competency_id"), a.get("module_id"), a.get("evidence_type")) for a in atts]
        assert len(keys) == len(set(keys)), f"Duplicate attainments found: {keys}"


# ---------- 2. RBAC ----------
class TestRBAC:
    @pytest.mark.skip(reason="Séparation des rôles supprimée (consolidation 2026-10 : admin unique + apprenants)")
    def test_author_cannot_list_users(self, tokens):
        r = requests.get(f"{API}/admin/users", headers=H(tokens["author"]), timeout=15)
        assert r.status_code == 403

    def test_admin_can_list_users(self, tokens):
        r = requests.get(f"{API}/admin/users", headers=H(tokens["admin"]), timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list) and len(r.json()) >= 6

    def test_learner_cannot_access_admin_users(self, tokens):
        r = requests.get(f"{API}/admin/users", headers=H(tokens["learner"]), timeout=15)
        assert r.status_code == 403

    def test_learner_cannot_access_admin_options(self, tokens):
        r = requests.get(f"{API}/admin/options", headers=H(tokens["learner"]), timeout=15)
        assert r.status_code == 403

    def test_author_can_access_admin_options(self, tokens):
        r = requests.get(f"{API}/admin/options", headers=H(tokens["author"]), timeout=15)
        assert r.status_code == 200


# ---------- 3. Admin user management ----------
class TestUserMgmt:
    email = f"test-u-{SFX}@ex.ci"
    uid = None

    def test_create_user(self, tokens):
        payload = {"email": self.email, "first_name": "Test", "last_name": "User",
                   "password": "Motdepasse1", "roles": ["author"], "role": "admin"}
        r = requests.post(f"{API}/admin/users", headers=H(tokens["admin"]), json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["email"] == self.email
        assert d["roles"] == ["learner"]
        assert "_id" not in d
        TestUserMgmt.uid = d["id"]

    @pytest.mark.skip(reason="Séparation des rôles supprimée (consolidation 2026-10 : admin unique + apprenants)")
    def test_patch_roles(self, tokens):
        assert TestUserMgmt.uid
        r = requests.patch(f"{API}/admin/users/{TestUserMgmt.uid}", headers=H(tokens["admin"]),
                           json={"roles": ["author", "reviewer"]}, timeout=15)
        assert r.status_code == 200
        assert set(r.json()["roles"]) == {"author", "reviewer"}

    def test_deactivate_and_login_blocked(self, tokens):
        tok = _login(self.email, "Motdepasse1")
        # deactivate
        r = requests.patch(f"{API}/admin/users/{TestUserMgmt.uid}", headers=H(tokens["admin"]),
                           json={"active": False}, timeout=15)
        assert r.status_code == 200
        # login now 403
        r2 = requests.post(f"{API}/auth/login", json={"email": self.email, "password": "Motdepasse1"}, timeout=15)
        assert r2.status_code == 403
        # existing token 401
        r3 = requests.get(f"{API}/auth/me", headers=H(tok), timeout=15)
        assert r3.status_code == 401

    def test_admin_cannot_self_deactivate(self, tokens):
        me = requests.get(f"{API}/auth/me", headers=H(tokens["admin"]), timeout=15).json()
        r = requests.patch(f"{API}/admin/users/{me['id']}", headers=H(tokens["admin"]),
                           json={"active": False}, timeout=15)
        assert r.status_code == 400

    def test_admin_cannot_drop_own_admin_role(self, tokens):
        me = requests.get(f"{API}/auth/me", headers=H(tokens["admin"]), timeout=15).json()
        r = requests.patch(f"{API}/admin/users/{me['id']}", headers=H(tokens["admin"]),
                           json={"roles": ["learner"]}, timeout=15)
        assert r.status_code == 400 and "Champ non autorisé" in r.json()["detail"]
        assert requests.get(f"{API}/auth/me", headers=H(tokens["admin"]), timeout=15).json()["roles"] == ["admin"]


# ---------- 4. PD01 concept workflow + 5. review return + 6. publish perms ----------
class TestConceptWorkflow:
    cid = f"test-concept-{SFX}"
    content = {"name": f"Notion Test {SFX}", "short": "s", "definition": "d", "example": "e",
               "treatment": {"L0": "a"}, "stage_ids": ["stage-01", "stage-04"],
               "layer_ids": ["layer-application", "layer-donnees", "layer-modeles"],
               "prerequisite_ids": ["concept-prompt"], "module_ids": ["M02"]}

    def test_create_draft(self, tokens):
        r = requests.post(f"{API}/admin/content/concept", headers=H(tokens["author"]),
                          json={"id": self.cid, "content": self.content}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["latest"]["status"] == "draft"
        assert r.json()["latest"]["version"] == 1

    def test_submit(self, tokens):
        r = requests.post(f"{API}/admin/versions/concept/{self.cid}/submit", headers=H(tokens["author"]), timeout=15)
        assert r.status_code == 200
        assert r.json()["latest"]["status"] == "review"

    @pytest.mark.skip(reason="Séparation des rôles supprimée (consolidation 2026-10 : admin unique + apprenants)")
    def test_author_cannot_publish(self, tokens):
        r = requests.post(f"{API}/admin/versions/concept/{self.cid}/publish", headers=H(tokens["author"]), timeout=15)
        assert r.status_code == 403

    def test_publish_without_approval(self, tokens):
        r = requests.post(f"{API}/admin/versions/concept/{self.cid}/publish", headers=H(tokens["lead"]), timeout=15)
        assert r.status_code == 409

    def test_return_requires_comment(self, tokens):
        r = requests.post(f"{API}/admin/versions/concept/{self.cid}/review", headers=H(tokens["reviewer"]),
                          json={"decision": "return", "comment": ""}, timeout=15)
        assert r.status_code == 400

    def test_return_with_comment(self, tokens):
        r = requests.post(f"{API}/admin/versions/concept/{self.cid}/review", headers=H(tokens["reviewer"]),
                          json={"decision": "return", "comment": "préciser l'exemple"}, timeout=15)
        assert r.status_code == 200
        j = r.json()
        assert j["latest"]["status"] == "draft"
        reviews = j["latest"].get("reviews", [])
        assert any("préciser" in (rv.get("comment") or "") for rv in reviews)

    def test_admin_resubmits_and_approves(self, tokens):
        requests.post(f"{API}/admin/versions/concept/{self.cid}/submit", headers=H(tokens["admin"]), timeout=15)
        r = requests.post(f"{API}/admin/versions/concept/{self.cid}/review", headers=H(tokens["admin"]),
                          json={"decision": "approve"}, timeout=15)
        assert r.status_code == 200 and r.json()["latest"]["approved"] is True

    def test_publish_by_lead(self, tokens):
        r = requests.post(f"{API}/admin/versions/concept/{self.cid}/publish", headers=H(tokens["lead"]), timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["latest"]["status"] == "published"

    def test_public_shows_concept(self, tokens):
        r = requests.get(f"{API}/concepts", timeout=15)
        assert r.status_code == 200
        matching = [c for c in r.json() if c["id"] == self.cid]
        assert len(matching) == 1

    def test_changelog_lists_events(self, tokens):
        r = requests.get(f"{API}/admin/changelog", headers=H(tokens["author"]),
                        params={"entity_id": self.cid}, timeout=15)
        assert r.status_code == 200
        rows = r.json()
        actions = {row["action"] for row in rows}
        assert {"create", "submit", "approve", "publish"}.issubset(actions), f"Got actions: {actions}"
        for row in rows:
            assert row.get("at") or row.get("created_at")
            assert row.get("user") or row.get("user_email")

    def test_changelog_filter_by_action(self, tokens):
        r = requests.get(f"{API}/admin/changelog", headers=H(tokens["author"]),
                        params={"entity_id": self.cid, "action": "publish"}, timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1
        assert all(row["action"] == "publish" for row in rows)


# ---------- 7. Module immutability / versioning / pin ----------
class TestModuleVersioning:
    def test_edit_published_creates_v2(self, tokens):
        r = requests.get(f"{API}/admin/content/module/M09", headers=H(tokens["author"]), timeout=15).json()
        mc = r["latest"]["content"]
        mc["summary"] = mc["summary"].rstrip() + " (test-v2)"
        r2 = requests.put(f"{API}/admin/content/module/M09", headers=H(tokens["author"]),
                          json={"content": mc, "changelog": "Révision test"}, timeout=15)
        assert r2.status_code == 200, r2.text
        latest = r2.json()["latest"]
        assert latest["version"] == 2
        assert latest["status"] == "draft"

    def test_edit_published_v1_blocked(self, tokens):
        mc = {"code": "M09", "summary": "x"}
        r = requests.put(f"{API}/admin/versions/module/M09/1", headers=H(tokens["author"]),
                        json={"content": mc}, timeout=15)
        assert r.status_code == 409

    def test_course_pin_unchanged(self, tokens):
        c = requests.get(f"{API}/courses/C03", timeout=15).json()
        pins = [m.get("pinned_version") for m in c["modules"] if m["id"] == "M09"]
        assert pins == [1], f"Expected M09 pinned v1 in C03, got {pins}"

    def test_public_module_still_v1(self, tokens):
        r = requests.get(f"{API}/modules/M09", timeout=15)
        assert r.status_code == 200
        # if the published projection stores version, it must still be 1
        v = r.json().get("version") or r.json().get("published_version")
        if v is not None:
            assert v == 1


# ---------- 8. Publication validation (cycle + unpublished course pin) ----------
class TestPubValidation:
    def test_cycle_blocked(self, tokens):
        a = f"test-cyc-a-{SFX}"
        b = f"test-cyc-b-{SFX}"
        base = TestConceptWorkflow.content
        # create & publish B with no prereq cycle
        b_content = dict(base, name=f"Cyc B {SFX}", prerequisite_ids=["concept-prompt"])
        requests.post(f"{API}/admin/content/concept", headers=H(tokens["author"]),
                      json={"id": b, "content": b_content}, timeout=15)
        requests.post(f"{API}/admin/versions/concept/{b}/submit", headers=H(tokens["author"]), timeout=15)
        requests.post(f"{API}/admin/versions/concept/{b}/review", headers=H(tokens["reviewer"]),
                      json={"decision": "approve"}, timeout=15)
        r = requests.post(f"{API}/admin/versions/concept/{b}/publish", headers=H(tokens["lead"]), timeout=15)
        assert r.status_code == 200
        # Create A with prereq B (ok). Publish it.
        a_content = dict(base, name=f"Cyc A {SFX}", prerequisite_ids=[b])
        requests.post(f"{API}/admin/content/concept", headers=H(tokens["author"]),
                      json={"id": a, "content": a_content}, timeout=15)
        requests.post(f"{API}/admin/versions/concept/{a}/submit", headers=H(tokens["author"]), timeout=15)
        requests.post(f"{API}/admin/versions/concept/{a}/review", headers=H(tokens["reviewer"]),
                      json={"decision": "approve"}, timeout=15)
        requests.post(f"{API}/admin/versions/concept/{a}/publish", headers=H(tokens["lead"]), timeout=15)
        # Now update B to require A → cycle A↔B
        b_content["prerequisite_ids"] = [a]
        requests.put(f"{API}/admin/content/concept/{b}", headers=H(tokens["author"]),
                     json={"content": b_content}, timeout=15)
        requests.post(f"{API}/admin/versions/concept/{b}/submit", headers=H(tokens["author"]), timeout=15)
        requests.post(f"{API}/admin/versions/concept/{b}/review", headers=H(tokens["reviewer"]),
                      json={"decision": "approve"}, timeout=15)
        r = requests.post(f"{API}/admin/versions/concept/{b}/publish", headers=H(tokens["lead"]), timeout=15)
        assert r.status_code == 422
        assert "Cycle" in (r.json().get("detail") or "")


# ---------- 10. History & diff ----------
class TestHistoryDiff:
    def test_versions_include_changes(self, tokens):
        r = requests.get(f"{API}/admin/versions/module/M09", headers=H(tokens["author"]), timeout=15)
        assert r.status_code == 200
        hist = r.json()
        assert isinstance(hist, list)
        assert len(hist) >= 2
        v2 = [h for h in hist if h.get("version") == 2]
        assert v2, f"No v2 in history: {[h.get('version') for h in hist]}"
        changes = v2[0].get("changes", [])
        assert any(c.get("field") == "summary" for c in changes), f"No summary diff in v2: {changes}"


# ---------- 11. Change log (filtered without entity_id) ----------
class TestChangelog:
    def test_log_endpoint_accessible(self, tokens):
        r = requests.get(f"{API}/admin/changelog", headers=H(tokens["author"]), timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        assert len(rows) > 0
        row = rows[0]
        assert row.get("action")
        assert row.get("at") or row.get("created_at")
        assert row.get("user") or row.get("user_email")

    def test_filter_by_action_publish(self, tokens):
        r = requests.get(f"{API}/admin/changelog", headers=H(tokens["author"]),
                        params={"action": "publish"}, timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert all(row["action"] == "publish" for row in rows)


# ---------- 12. Analytics / events ----------
class TestAnalytics:
    def test_event_anonymous(self):
        r = requests.post(f"{API}/events", json={"type": "demo_start", "session_id": f"s-{SFX}", "step": 1}, timeout=15)
        assert r.status_code == 200
        r2 = requests.post(f"{API}/events", json={"type": "demo_layer_click", "layer_id": "layer-donnees", "step": 2}, timeout=15)
        assert r2.status_code == 200

    def test_event_validates_type(self):
        r = requests.post(f"{API}/events", json={"type": "bad_event"}, timeout=15)
        assert r.status_code == 422

    def test_analytics_counts(self, tokens):
        r = requests.get(f"{API}/admin/analytics", headers=H(tokens["lead"]), timeout=15)
        assert r.status_code == 200
        j = r.json()
        assert "demo" in j
        assert j["demo"]["starts"] >= 1
        assert j["demo"]["layer_clicks"] >= 1


# ---------- 13. Public regression (Phase 1-3) ----------
class TestRegression:
    def test_openapi_public(self):
        r = requests.get(f"{API}/openapi.json", timeout=15)
        assert r.status_code == 200
        assert "paths" in r.json()

    def test_concepts_public(self):
        r = requests.get(f"{API}/concepts", timeout=15)
        assert r.status_code == 200 and len(r.json()) > 0

    def test_modules_public(self):
        r = requests.get(f"{API}/modules/M01", timeout=15)
        assert r.status_code == 200

    def test_pathway_progress(self, tokens):
        r = requests.get(f"{API}/learners/me/pathways/P02/progress", headers=H(tokens["learner"]), timeout=15)
        assert r.status_code in (200, 404)  # 404 if not enrolled → still a valid API response

    def test_courses_c03(self):
        r = requests.get(f"{API}/courses/C03", timeout=15)
        assert r.status_code == 200
        assert any(m["id"] == "M09" for m in r.json()["modules"])
