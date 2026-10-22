"""Read-only verifications for iteration 10 — flag CASA_EXTRA_ATTEMPT_GRANTS OFF (preprod 8001).
STRICT: only POST /api/auth/login + GET. No writes."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://relais-footer.preview.emergentagent.com").rstrip("/")
ADMIN = {"email": "admin@casa-academy.com", "password": "Admin2026!"}
LEARNER = {"email": "apprenant@casa-academy.ci", "password": "Apprenant2026!"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_h():
    return {"Authorization": f"Bearer {_login(ADMIN)}"}


@pytest.fixture(scope="module")
def learner_h():
    return {"Authorization": f"Bearer {_login(LEARNER)}"}


# --- Backend fix for module_progress with flag OFF ---
def test_module_progress_graded_has_no_max_attempts(learner_h):
    """With CASA_EXTRA_ATTEMPT_GRANTS OFF, module_progress 'graded' must NOT contain max_attempts."""
    # Pick a module that has a graded assessment (M-003 known; else fallback discovery via dashboard).
    tried = []
    for mid in ("M-003", "M01", "M02", "M03"):
        r = requests.get(f"{BASE_URL}/api/learners/me/modules/{mid}/progress", headers=learner_h, timeout=20)
        tried.append((mid, r.status_code))
        if r.status_code == 200:
            data = r.json()
            if data.get("graded"):
                assert "max_attempts" not in data["graded"], f"[{mid}] graded leaked max_attempts: {data['graded']}"
                print(f"OK module {mid} graded keys = {sorted(data['graded'].keys())}")
                return
    pytest.fail(f"No module with graded progression found. Tried: {tried}")


def test_admin_attempt_grants_endpoint_unavailable(admin_h):
    """Flag OFF: /api/admin/attempt-grants must return 404 (grants_enabled dependency)."""
    r = requests.get(f"{BASE_URL}/api/admin/attempt-grants", headers=admin_h, timeout=15)
    assert r.status_code == 404, f"Expected 404 with flag OFF, got {r.status_code}: {r.text[:200]}"


# --- Review report "regle-repli-niveau" ---
def test_reports_list_contains_regle_repli(admin_h):
    r = requests.get(f"{BASE_URL}/api/admin/reports", headers=admin_h, timeout=15)
    assert r.status_code == 200
    ids = {x["id"]: x for x in r.json()}
    assert "regle-repli-niveau" in ids
    assert ids["regle-repli-niveau"]["available"] is True


def test_report_regle_repli_md(admin_h):
    r = requests.get(f"{BASE_URL}/api/admin/reports/regle-repli-niveau", params={"format": "md"}, headers=admin_h, timeout=20)
    assert r.status_code == 200
    assert "Règle de repli" in r.text
    assert "CASA_LEVEL_FROM_ASSESSMENT_MODULE_VERSION" in r.text


def test_report_regle_repli_pdf(admin_h):
    r = requests.get(f"{BASE_URL}/api/admin/reports/regle-repli-niveau", params={"format": "pdf"}, headers=admin_h, timeout=30)
    assert r.status_code == 200
    assert r.content[:5] == b"%PDF-", f"Not a PDF, starts with: {r.content[:16]!r}"
    assert "application/pdf" in r.headers.get("content-type", "")


# --- Review queue export ---
def test_review_queue_export_md_has_section_and_20_items(admin_h):
    r = requests.get(f"{BASE_URL}/api/admin/review-queue/export", params={"format": "md"}, headers=admin_h, timeout=30)
    assert r.status_code == 200
    md = r.text
    assert "## Règle de repli (quiz déjà publiés)" in md
    # Count elements declared in header: "N élément(s) en brouillon ou en relecture."
    import re
    m = re.search(r"(\d+)\s+élément\(s\) en brouillon ou en relecture", md)
    assert m, "Header count missing"
    assert m.group(1) == "20", f"Expected 20 items, got {m.group(1)}"


def test_review_queue_export_pdf(admin_h):
    r = requests.get(f"{BASE_URL}/api/admin/review-queue/export", params={"format": "pdf"}, headers=admin_h, timeout=45)
    assert r.status_code == 200
    assert r.content[:5] == b"%PDF-"
