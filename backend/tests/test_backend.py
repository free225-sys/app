"""Backend API tests for CASA AI Academy Phase 1."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://relais-footer.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def s():
    return requests.Session()


# ---------- Catalog ----------
def test_openapi(s):
    r = s.get(f"{API}/openapi.json")
    assert r.status_code == 200
    assert "paths" in r.json()


def test_stages(s):
    r = s.get(f"{API}/catalog/stages")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 7
    assert all("id" in d and "code" in d for d in data)


def test_layers(s):
    r = s.get(f"{API}/catalog/layers")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 6
    for layer in data:
        assert "modules" in layer
        assert isinstance(layer["modules"], list)


def test_overview(s):
    r = s.get(f"{API}/catalog/overview")
    assert r.status_code == 200
    d = r.json()
    for k in ["stages", "phases", "layers", "competencies", "levels", "profiles", "version_statuses"]:
        assert k in d


# ---------- Demo ----------
def test_demo_scenario(s):
    r = s.get(f"{API}/demo/scenarios/casa-jo-cafe-cacao")
    assert r.status_code == 200
    d = r.json()
    assert len(d["steps"]) == 7
    assert len(d["quiz"]) == 3


def test_demo_scenario_404(s):
    assert s.get(f"{API}/demo/scenarios/unknown").status_code == 404


# ---------- Concepts ----------
def test_concepts_list(s):
    r = s.get(f"{API}/concepts")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 35


def test_concepts_filters_combined(s):
    r = s.get(f"{API}/concepts", params={
        "stage": "stage-03", "layer": "layer-donnees",
        "level": "L2", "competency": "comp-construire", "q": "rag"
    })
    assert r.status_code == 200
    data = r.json()
    # Accent-insensitive search check
    for c in data:
        assert "stage-03" in c["stage_ids"]
        assert "layer-donnees" in c["layer_ids"]


def test_concept_accent_insensitive(s):
    # 'donnee' should match 'données'
    r = s.get(f"{API}/concepts", params={"q": "donnees"})
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_concept_rag(s):
    r = s.get(f"{API}/concepts/concept-rag")
    assert r.status_code == 200
    d = r.json()
    assert d["id"] == "concept-rag"
    for k in ["stages", "layers", "prerequisites", "modules", "dependents"]:
        assert k in d


def test_concept_404(s):
    assert s.get(f"{API}/concepts/unknown-xyz").status_code == 404


# ---------- Modules ----------
def test_modules_list(s):
    r = s.get(f"{API}/modules")
    assert r.status_code == 200
    assert len(r.json()) >= 16


def test_modules_filters(s):
    r = s.get(f"{API}/modules", params={"stage": "stage-03", "layer": "layer-donnees", "level": "L2",
                                        "competency": "comp-construire", "q": "rag"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_module_m09(s):
    r = s.get(f"{API}/modules/M09")
    assert r.status_code == 200
    d = r.json()
    assert d["code"] == "M09"
    assert d["version"] == 1
    assert d["status"] == "published"
    assert len(d["resources"]) == 4
    course_ids = {c["id"] for c in d["courses"]}
    assert "C02" in course_ids and "C03" in course_ids


def test_module_versions(s):
    r = s.get(f"{API}/modules/M09/versions")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_module_404(s):
    assert s.get(f"{API}/modules/M99").status_code == 404
    assert s.get(f"{API}/modules/M99/versions").status_code == 404


# ---------- Courses & pathways ----------
def test_courses_list(s):
    r = s.get(f"{API}/courses")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_course_c03(s):
    r = s.get(f"{API}/courses/C03")
    assert r.status_code == 200
    d = r.json()
    assert d["code"] == "C03"
    assert any(m["id"] == "M09" for m in d["modules"])


def test_course_404(s):
    assert s.get(f"{API}/courses/C99").status_code == 404


def test_pathways_list(s):
    r = s.get(f"{API}/pathways")
    assert r.status_code == 200
    data = r.json()
    ids = {p["id"] for p in data}
    assert "P01" in ids and "P02" in ids


def test_pathway_p01(s):
    r = s.get(f"{API}/pathways/P01")
    assert r.status_code == 200
    d = r.json()
    assert "courses" in d
    assert len(d["courses"]) >= 1


def test_pathway_404(s):
    assert s.get(f"{API}/pathways/P99").status_code == 404


def test_m09_shared_in_c02_c03(s):
    # Verify M09 appears in both C02 and C03
    r2 = s.get(f"{API}/courses/C02").json()
    r3 = s.get(f"{API}/courses/C03").json()
    assert any(m["id"] == "M09" for m in r2["modules"])
    assert any(m["id"] == "M09" for m in r3["modules"])
