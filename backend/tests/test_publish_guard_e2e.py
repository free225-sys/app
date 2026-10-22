"""Publication guard for credential attainability — runs ONLY against the isolated instance 127.0.0.1:8002."""
from test_revocation_block import admin, call, db, guard  # noqa: F401

CL = "QA E2E contrôle de publication"
META = {"_id", "id", "entity_id", "question_id", "version", "status", "approved", "changelog", "created_at", "created_by", "updated_at", "updated_by",
        "submitted_at", "submitted_by", "reviews", "published_at", "published_by", "superseded"}


def content(adm, t, eid, v):
    st, d = call("GET", f"/admin/versions/{t}/{eid}/{v}", adm)
    assert st == 200, d
    return {k: x for k, x in d.get("content", d).items() if k not in META}


def draft(adm, t, eid, c, new=False):
    st, d = call("POST", f"/admin/content/{t}", adm, {"id": eid, "content": c, "changelog": CL}) if new else call("PUT", f"/admin/content/{t}/{eid}", adm, {"content": c, "changelog": CL})
    assert st == 200, d
    assert call("POST", f"/admin/versions/{t}/{eid}/submit", adm)[0] == 200
    assert call("POST", f"/admin/versions/{t}/{eid}/review", adm, {"decision": "approve", "comment": CL})[0] == 200
    return d["latest"]["version"]


def publish(adm, t, eid):
    return call("POST", f"/admin/versions/{t}/{eid}/publish", adm)


def test_m003_without_k001_refused_until_m001_route_published(db, admin):  # noqa: F811
    guard()
    new = {}
    for q in ("Q-M-003-G1", "Q-M-003-G3", "Q-M-003-G5"):
        c = content(admin, "question", q, 1)
        c["competencies"] = [w for w in c["competencies"] if w["competency_id"] != "K-001"]
        new[q] = draft(admin, "question", q, c)
        assert publish(admin, "question", q)[0] == 200
    a = content(admin, "assessment", "A-M-003-G", 1)
    a["questions"] = [{"question_id": q["question_id"], "version": new.get(q["question_id"], q["version"])} for q in a["questions"]]
    draft(admin, "assessment", "A-M-003-G", a)
    st, d = publish(admin, "assessment", "A-M-003-G")
    assert st == 422 and "CERT-DOC-01 règle r1 : K-001 niveau L1" in d["detail"], d
    assert db.assessments.find_one({"_id": "A-M-003-G"})["published_version"] == 1

    q = content(admin, "question", "Q-M-003-G2", 1)
    q.update(module_id="M-001", competencies=[{"competency_id": "K-001", "weight": 1}])
    draft(admin, "question", "Q-E2E-K001", q, new=True)
    assert publish(admin, "question", "Q-E2E-K001")[0] == 200
    g = {**a, "code": "A-E2E-M001-G", "module_id": "M-001", "title": "QA E2E quiz noté M-001", "questions": [{"question_id": "Q-E2E-K001", "version": 1}]}
    draft(admin, "assessment", "A-E2E-M001-G", g, new=True)
    assert publish(admin, "assessment", "A-E2E-M001-G")[0] == 200
    st, d = publish(admin, "assessment", "A-M-003-G")
    assert st == 422, "M-001 encore en L0 : K-001 L1 toujours inatteignable"
    m = content(admin, "module", "M-001", 1)
    m.update(levels=["L0", "L1"], assessment_ids=m["assessment_ids"] + ["A-E2E-M001-G"])
    draft(admin, "module", "M-001", m)
    assert publish(admin, "module", "M-001")[0] == 200
    st, d = publish(admin, "assessment", "A-M-003-G")
    assert st == 200, d
    assert db.assessments.find_one({"_id": "A-M-003-G"})["published_version"] == 2
