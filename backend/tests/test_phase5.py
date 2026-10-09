"""Phase 5 — Footer/Relais IT, prototype UX catalog, import/export, delete draft, CERT-DOC-01."""
import io
import os
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://relais-footer.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

CREDS = {
    "admin": ("admin@casa-academy.ci", "Admin2026!"),
    "lead": ("lead@casa-academy.ci", "Responsable2026!"),
    "author": ("author@casa-academy.ci", "Auteur2026!"),
    "learner": ("apprenant@casa-academy.ci", "Apprenant2026!"),
}


def login(role):
    email, pw = CREDS[role]
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, f"login {role} failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def H(role_or_tok):
    tok = role_or_tok if role_or_tok.count(".") == 2 else login(role_or_tok)
    return {"Authorization": f"Bearer {tok}"}


# ---------- Catalog content ----------

class TestCatalogContent:
    def test_modules_include_m01_and_m_001(self):
        r = requests.get(f"{API}/modules", timeout=15)
        assert r.status_code == 200
        ids = {m["id"] for m in r.json()}
        for want in ["M01", "M-001", "M-002", "M-003"]:
            assert want in ids, f"module {want} missing — got {sorted(ids)}"

    def test_courses_include_co(self):
        r = requests.get(f"{API}/courses", timeout=15)
        assert r.status_code == 200
        ids = {c["id"] for c in r.json()}
        assert {"CO-001", "CO-002"} <= ids, f"got {sorted(ids)}"

    def test_pathways_include_p(self):
        r = requests.get(f"{API}/pathways", timeout=15)
        assert r.status_code == 200
        ids = {p["id"] for p in r.json()}
        assert {"P-001", "P-002"} <= ids, f"got {sorted(ids)}"

    def test_credentials_include_cert_doc_01(self):
        r = requests.get(f"{API}/credentials", timeout=15)
        assert r.status_code == 200
        ids = {c["id"] for c in r.json()}
        assert "CERT-DOC-01" in ids

    def test_competencies_include_k(self):
        # not a public endpoint — fetch via export (lead)
        tok = login("lead")
        r = requests.get(f"{API}/admin/catalog/export", headers=H(tok), timeout=20)
        assert r.status_code == 200
        comp_ids = {k["id"] for k in r.json()["competencies"]}
        assert {"K-001", "K-002", "K-003"} <= comp_ids


# ---------- Export / Import ----------

class TestCatalogIO:
    def test_author_cannot_export(self):
        r = requests.get(f"{API}/admin/catalog/export", headers=H("author"), timeout=15)
        assert r.status_code == 403

    def test_author_cannot_import(self):
        r = requests.post(f"{API}/admin/catalog/import", json={"catalogue_version": "x"}, headers=H("author"), timeout=15)
        assert r.status_code == 403

    def test_export_shape(self):
        r = requests.get(f"{API}/admin/catalog/export", headers=H("lead"), timeout=20)
        assert r.status_code == 200
        data = r.json()
        for k in ["catalogue_version", "stages", "layers", "concepts", "competencies",
                  "modules", "learning_assets", "courses", "pathways", "assessments",
                  "credential_examples", "reuse_rule"]:
            assert k in data, f"missing {k}"
        assert data["reuse_rule"].startswith("Une ressource")

    def test_reimport_export_unchanged(self):
        tok = login("lead")
        exp = requests.get(f"{API}/admin/catalog/export", headers=H(tok), timeout=20).json()
        r = requests.post(f"{API}/admin/catalog/import", json=exp, headers=H(tok), timeout=30)
        assert r.status_code == 200, r.text
        out = r.json()
        s = out["summary"]
        assert s["errors"] == 0, out["errors"]
        assert s["create"] == 0, [i for i in out["items"] if i["action"] == "create"]
        assert s["update"] == 0, [i for i in out["items"] if i["action"] == "update"]

    def test_broken_ref_rejected_on_confirm(self):
        tok = login("lead")
        exp = requests.get(f"{API}/admin/catalog/export", headers=H(tok), timeout=20).json()
        # inject broken concept reference inside a module
        bad = {**exp, "modules": [dict(m) for m in exp["modules"]]}
        bad["modules"][0]["concepts"] = list(bad["modules"][0].get("concepts", [])) + ["C-999-does-not-exist"]
        # preview: should list errors
        prev = requests.post(f"{API}/admin/catalog/import", json=bad, headers=H(tok), timeout=30).json()
        assert prev["summary"]["errors"] >= 1
        assert any("C-999" in e for e in prev["errors"])
        # confirm: must reject with 422
        conf = requests.post(f"{API}/admin/catalog/import?confirm=true", json=bad, headers=H(tok), timeout=30)
        assert conf.status_code == 422
        assert "Import refusé" in conf.json().get("detail", "")

    def test_confirm_tiny_change_creates_draft_and_cleanup(self):
        tok = login("lead")
        exp = requests.get(f"{API}/admin/catalog/export", headers=H(tok), timeout=20).json()
        # pick first course, change its title with a tagged suffix
        suffix = f" (TEST-{uuid.uuid4().hex[:6]})"
        courses = [dict(c) for c in exp["courses"]]
        target_cid = courses[0]["id"]
        courses[0]["title"] = courses[0]["title"] + suffix
        tiny = {**exp, "courses": courses}
        prev = requests.post(f"{API}/admin/catalog/import", json=tiny, headers=H(tok), timeout=30).json()
        assert prev["summary"]["errors"] == 0, prev["errors"]
        assert prev["summary"]["update"] >= 1
        # confirm
        conf = requests.post(f"{API}/admin/catalog/import?confirm=true", json=tiny, headers=H(tok), timeout=30)
        assert conf.status_code == 200, conf.text
        # new draft on the targeted course exists
        hist = requests.get(f"{API}/admin/versions/course/{target_cid}", headers=H(tok), timeout=15)
        assert hist.status_code == 200, hist.text
        drafts = [v for v in hist.json() if v["status"] == "draft"]
        assert drafts, "no draft after confirm import"
        # cleanup — delete the latest draft
        v = drafts[-1]["version"]
        d = requests.delete(f"{API}/admin/versions/course/{target_cid}/{v}", headers=H(tok), timeout=15)
        assert d.status_code == 200, d.text


# ---------- Delete draft ----------

class TestDeleteDraft:
    def test_published_delete_returns_409(self):
        tok = login("lead")
        # M01 published v1 cannot be deleted
        r = requests.delete(f"{API}/admin/versions/module/M01/1", headers=H(tok), timeout=15)
        assert r.status_code == 409

    def test_author_can_delete_own_draft(self):
        author_tok = login("author")
        # Create a new concept draft owned by author
        sfx = uuid.uuid4().hex[:6]
        eid = f"test-c-{sfx}"
        payload = {
            "id": eid,
            "content": {
                "name": f"Notion test {sfx}",
                "short": "x", "definition": "y", "example": "z",
                "stage_ids": [], "layer_ids": [], "module_ids": [],
                "prerequisite_ids": [], "treatment": {},
            },
            "changelog": "test",
        }
        r = requests.post(f"{API}/admin/content/concept", json=payload, headers=H(author_tok), timeout=15)
        assert r.status_code == 200, r.text
        # delete as author
        d = requests.delete(f"{API}/admin/versions/concept/{eid}/1", headers=H(author_tok), timeout=15)
        assert d.status_code == 200, d.text


# ---------- Certificate PDF content ----------

class TestCertificatePDF:
    def test_pdf_contains_relais_it(self):
        # Use admin's own existing certificate if any; otherwise skip gracefully.
        tok = login("admin")
        # list all certificates (admin)
        r = requests.get(f"{API}/admin/certificates", headers=H(tok), timeout=15)
        assert r.status_code == 200
        certs = r.json()
        # pick a cert belonging to admin learner acct — fallback to any valid
        valid = [c for c in certs if c["status"] == "valid"]
        if not valid:
            pytest.skip("no valid certificate in system")
        code = valid[0]["code"]
        pdf = requests.get(f"{API}/certificates/{code}/pdf", headers=H(tok), timeout=20)
        assert pdf.status_code == 200, pdf.text
        assert pdf.headers.get("content-type", "").startswith("application/pdf")
        body = pdf.content
        assert b"%PDF" in body[:8]
        # Extract text with pypdf
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(body))
        text = "\n".join(p.extract_text() or "" for p in reader.pages)
        assert "Relais IT" in text, f"PDF should contain 'Relais IT'. text={text!r}"
        assert "by" in text
        assert "www.relaisit.com" not in text, (
            "spec says 'www.relaisit.com' visible text must NOT appear in the PDF; only link annotation URI"
        )
        # Link annotation URI to relaisit.com must be present in raw bytes
        assert b"https://www.relaisit.com" in body, "link annotation to relaisit.com must be present"


# ---------- CERT-DOC-01 claim ----------

def register_fresh_learner():
    sfx = uuid.uuid4().hex[:8]
    email = f"test-learner-{sfx}@casa-academy.ci"
    pw = "Learner2026!"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": pw, "first_name": "Test", "last_name": sfx,
        "profile_id": "profile-decouvrir",
    }, timeout=15)
    assert r.status_code in (200, 201), r.text
    tok = r.json().get("access_token") or login_raw(email, pw)
    return email, pw, tok


def login_raw(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200
    return r.json()["access_token"]


class TestCertDoc01Claim:
    def test_m001_has_no_graded_step(self):
        r = requests.get(f"{API}/modules/M-001", timeout=15)
        assert r.status_code == 200
        mod = r.json()
        assert mod.get("completion_rule") == "resources" or not any(
            a.get("kind") == "graded" for a in mod.get("assessments", [])
        ), f"M-001 should not have a graded step: {mod.get('assessments')}"

    def test_claim_denied_without_evidence(self):
        _, _, tok = register_fresh_learner()
        r = requests.post(f"{API}/credentials/CERT-DOC-01/claim", headers=H(tok), timeout=15)
        assert r.status_code == 400
        assert "non remplies" in r.json().get("detail", "")

    def test_full_claim_cert_doc_01(self):
        _, _, tok = register_fresh_learner()
        headers = H(tok)
        # Mark A-005 (M-003 resource) as completed
        done = requests.post(f"{API}/learners/me/resources/A-005/complete", headers=headers, timeout=15)
        # endpoint path may differ, try alternatives
        if done.status_code == 404:
            done = requests.post(f"{API}/learners/me/modules/M-003/resources/A-005/complete", headers=headers, timeout=15)
        assert done.status_code in (200, 201, 204), f"complete A-005: {done.status_code} {done.text}"

        # Submit graded quiz A-M-003-G with correct answers
        answers = {
            "Q-M-003-G1": ["b"],
            "Q-M-003-G2": ["b"],
            "Q-M-003-G3": ["a", "b", "d"],
            "Q-M-003-G4": ["b"],
            "Q-M-003-G5": ["a"],
        }
        att = requests.post(f"{API}/assessments/A-M-003-G/attempts",
                            json={"answers": answers}, headers=headers, timeout=20)
        assert att.status_code == 200, att.text
        a = att.json()["attempt"]
        assert a["passed"], f"quiz should pass with correct answers, got {a['percent']}"

        # Claim credential
        claim = requests.post(f"{API}/credentials/CERT-DOC-01/claim", headers=headers, timeout=15)
        assert claim.status_code == 200, claim.text
        award = claim.json()
        assert award["status"] == "valid"
        assert award["code"].startswith("CASA-")
