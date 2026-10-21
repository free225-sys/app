"""Phase 6 — CASA AI Academy: lisibilité et respiration.
Backend checks: estimated_minutes present and int on modules/concepts/courses.
"""
import os
import requests
from dotenv import load_dotenv
from creds import LEARNER

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


class TestEstimatedMinutes:
    def test_module_m09_estimated_minutes(self):
        r = requests.get(f"{BASE_URL}/api/modules/M09", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "estimated_minutes" in data
        assert isinstance(data["estimated_minutes"], int)
        assert data["estimated_minutes"] >= 1
        # Summary card expectations
        assert data.get("levels") == ["L2", "L3"] or set(data.get("levels", [])) >= {"L2", "L3"}
        prereq_ids = [p["id"] for p in data.get("prerequisite_modules", [])]
        assert "M02" in prereq_ids and "M08" in prereq_ids, prereq_ids

    def test_concept_rag_estimated_minutes(self):
        r = requests.get(f"{BASE_URL}/api/concepts/concept-rag", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data.get("estimated_minutes"), int)
        assert data["estimated_minutes"] >= 1
        # Treatment should have L0-L4
        tr = data.get("treatment") or {}
        for lv in ("L0", "L1", "L2", "L3", "L4"):
            assert lv in tr, f"missing {lv}"

    def test_course_c03_estimated_minutes(self):
        r = requests.get(f"{BASE_URL}/api/courses/C03", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data.get("estimated_minutes"), int)
        # Each module in course should also have estimated_minutes
        mods = data.get("modules", [])
        assert mods
        for m in mods:
            assert isinstance(m.get("estimated_minutes"), int) and m["estimated_minutes"] >= 1


class TestAuthForFrontendFlow:
    def test_learner_login(self):
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": LEARNER[0], "password": LEARNER[1]},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        assert "access_token" in r.json()
