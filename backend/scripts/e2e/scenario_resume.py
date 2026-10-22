"""Resume CERT-DOC-01 scenario from step 5 on the casa_e2e clone (steps 0-4 already run by scenario.py)."""
import io
import json
import os
from datetime import datetime, timedelta, timezone

import jwt
from pymongo import MongoClient
from pypdf import PdfReader

import scenario as sc
from scenario import ADMIN, D, S, correct, courses_of, db, guard, log, register

prod = MongoClient(os.environ["MONGO_URL"])["test_database"]


def clone_session(email):
    """Access token for a qa-e2e learner, signed with the clone instance's own secret (never printed)."""
    u = db.users.find_one({"email": email})
    assert email.startswith("qa-e2e-")
    tok = jwt.encode({"sub": str(u["_id"]), "type": "access", "sv": u.get("session_version", 0), "exp": datetime.now(timezone.utc) + timedelta(minutes=30)},
                     (D / "jwt_secret").read_text().strip(), algorithm="HS256")
    return S(tok), str(u["_id"])


def existing_state(database):
    qa = {str(u["_id"]) for u in database.users.find({"email": {"$regex": "^qa-e2e-"}})}
    out = {}
    for c in ("users", "enrollments", "module_completions", "attainments", "awards", "attempts", "resource_progress"):
        key = "_id" if c == "users" else "user_id"
        out[c] = sorted(json.dumps(d, sort_keys=True, default=str) for d in database[c].find({}) if str(d.get(key)) not in qa)
    return out


def main():
    guard()
    st, data = S().req("POST", "/auth/login", {"email": ADMIN[0], "password": ADMIN[1]})
    admin = S(data["access_token"])
    a, aid_ = clone_session("qa-e2e-a@example.com")
    c, cid = clone_session("qa-e2e-c@example.com")

    av = db.assessment_versions.find_one({"entity_id": "A-M-003-G", "status": "published"}, sort=[("version", -1)])
    qids = [q["question_id"] for q in av["questions"]]
    st, r5 = a.req("POST", "/assessments/A-M-003-G/attempts", {"answers": {q: correct(q) for q in qids}})
    atts = list(db.attainments.find({"user_id": aid_}, {"_id": 0, "competency_id": 1, "level": 1, "score_percent": 1, "module_id": 1}))
    st_c, award = a.req("POST", "/credentials/CERT-DOC-01/claim")
    log("5", "A-M-003-G réussi puis réclamation", http=st, assessment_version=av["version"], score=f"{r5['attempt']['score']}/{r5['attempt']['max_score']}",
        passed=r5["attempt"]["passed"], attainments=atts, claim_http=st_c, code=award.get("code"), status=award.get("status"),
        verification_url=award.get("verification_url"), evidence=[(e["rule_id"], e.get("module_id"), e.get("score_percent")) for e in award.get("evidence_refs", [])])
    code = award["code"]

    b, _ = register("b")
    res = {}
    for who_, sess in (("titulaire", a), ("admin", admin), ("autre apprenant qa-e2e-B", b), ("visiteur", S())):
        st, body = sess.req("GET", f"/certificates/{code}/pdf")
        res[who_] = st
        if who_ == "titulaire" and st == 200:
            (D / "certificat-clone.pdf").write_bytes(body)
            os.chmod(D / "certificat-clone.pdf", 0o600)
            text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(body)).pages)
            res["pdf_mention_clone"] = "CLONE E2E — sans valeur" in text
            res["pdf_url_locale"] = f"http://localhost:8002/verifier/{code}" in text
            res["pdf_url_publique"] = "preview.emergentagent.com" in text
    log("6", "accès au PDF", **res)
    st, v = S().req("GET", f"/verify/{code}")
    log("6", "vérification publique sur 8002", http=st, status=v.get("status"), holder=v.get("holder_name"), evidence=v.get("evidence"))
    st, rv = admin.req("POST", f"/admin/certificates/{code}/revoke", {"reason": "E2E clone : test de révocation"})
    _, v = S().req("GET", f"/verify/{code}")
    st_pdf, _ = a.req("GET", f"/certificates/{code}/pdf")
    log("6", "révocation par l'admin du clone", http=st, status=rv.get("status"), verify_status=v.get("status"), revoke_reason=v.get("revoke_reason"), holder_pdf_http=st_pdf)
    st_re, re_ = a.req("POST", "/credentials/CERT-DOC-01/claim")
    _, v = S().req("GET", f"/verify/{code}")
    k_after = list(db.attainments.find({"user_id": aid_}, {"_id": 0, "competency_id": 1, "status": 1}))
    log("6", "après révocation : nouvelle réclamation et statut de l'ancien code", claim_http=st_re,
        new_code=re_.get("code") if isinstance(re_, dict) else None, claim_detail=re_.get("detail") if isinstance(re_, dict) else None,
        old_code_status=v.get("status"), attainments=k_after)

    before, after = existing_state(prod), existing_state(db)
    log("7", "comptes et données des apprenants existants : clone après publication vs préproduction",
        identiques={k: (len(before[k]), len(after[k]), before[k] == after[k]) for k in before})
    st, prog = c.req("GET", "/learners/me/modules/M-001/progress")
    _, cprog = c.req("GET", "/learners/me/pathways/P-001/progress")
    st_c, dc = c.req("POST", "/credentials/CERT-DOC-01/claim")
    log("7", "qa-e2e-C après publication", http=st, status=prog.get("status"), module_version=prog.get("module_version"),
        previous_completion=prog.get("previous_completion"), attainments=db.attainments.count_documents({"user_id": cid}),
        awards=db.awards.count_documents({"user_id": cid}), claim_http=st_c, claim_detail=dc.get("detail"),
        completions=list(db.module_completions.find({"user_id": cid}, {"_id": 0, "module_id": 1, "module_version": 1})),
        enrollment=db.enrollments.find_one({"user_id": cid}, {"_id": 0, "pathway_version": 1}), pathway=courses_of(cprog))

    dd, did = register("d")
    st, _ = dd.req("POST", "/pathways/P-001/enroll")
    _, dprog = dd.req("GET", "/learners/me/pathways/P-001/progress")
    log("8", "nouvel inscrit qa-e2e-D sur P-001", http=st, enrollment=db.enrollments.find_one({"user_id": did}, {"_id": 0, "pathway_version": 1}),
        pathway=courses_of(dprog))

    (D / "scenario_report_suite.json").write_text(json.dumps(sc.REPORT, ensure_ascii=False, indent=1, default=str))
    os.chmod(D / "scenario_report_suite.json", 0o600)


if __name__ == "__main__":
    main()
