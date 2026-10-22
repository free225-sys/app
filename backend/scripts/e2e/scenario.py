"""CERT-DOC-01 end-to-end scenario, run ONLY against the casa_e2e clone served on 127.0.0.1:8002."""
import io
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from pymongo import MongoClient
from pypdf import PdfReader

sys.path.insert(0, "/app/backend/tests")
from creds import ADMIN  # noqa: E402

load_dotenv("/app/backend/.env", override=False)
E2E, PORT = "casa_e2e", 8002
BASE = f"http://127.0.0.1:{PORT}/api"
D = Path("/app/backups/e2e")
db = MongoClient(os.environ["MONGO_URL"])[E2E]
REPORT = []
ORDER = [("question", f"Q-M-001-G{i}") for i in range(1, 6)] + [("assessment", "A-M-001-G"), ("module", "M-001"),
         ("course", "CO-001"), ("course", "CO-002"), ("pathway", "P-001"), ("pathway", "P-002")]


def guard():
    pid = (D / "8002.pid").read_text().strip()
    env = dict(x.split("=", 1) for x in Path(f"/proc/{pid}/environ").read_bytes().decode().split("\0") if "=" in x)
    cmd = Path(f"/proc/{pid}/cmdline").read_bytes().decode().split("\0")
    if env.get("DB_NAME") != E2E or env.get("CASA_TEST_DB") != E2E or "--port" not in cmd or cmd[cmd.index("--port") + 1] != str(PORT) \
            or not BASE.startswith(f"http://127.0.0.1:{PORT}/"):
        sys.exit("ARRÊT : la cible n'est pas casa_e2e sur le port 8002")


class S:
    def __init__(self, token=None):
        self.h = {"Authorization": f"Bearer {token}"} if token else {}

    def req(self, method, path, body=None):
        if method != "GET":
            guard()
        r = requests.request(method, BASE + path, json=body, headers=self.h, timeout=60)
        try:
            data = r.json()
        except ValueError:
            data = r.content
        return r.status_code, data


def log(step, label, **kw):
    REPORT.append({"step": step, "label": label, **kw})
    print(f"[{step}] {label} :: " + json.dumps(kw, ensure_ascii=False, default=str)[:900])


def register(tag):
    st, data = S().req("POST", "/auth/register", {"first_name": "QA", "last_name": f"E2E {tag.upper()}",
                                                    "email": f"qa-e2e-{tag}@example.com", "password": "QaE2e-" + os.urandom(6).hex()})
    assert st == 200, (st, data)
    return S(data["access_token"]), data["user"]["id"]


def correct(qid):
    q = db.questions.find_one({"entity_id": qid, "status": "published"}, sort=[("version", -1)]) or db.questions.find_one({"entity_id": qid}, sort=[("version", -1)])
    return list((q.get("content") or q)["correct"])


def courses_of(p):
    return [(c["course_id"], c["course_version"], [(m["module_id"], m["module_version"], m["status"]) for m in c["modules"]])
            for g in p["groups"].values() for c in g] + [("pathway_version", p["pathway_version"])]


def others_snapshot():
    qa = {str(u["_id"]) for u in db.users.find({"email": {"$regex": "^qa-e2e-"}})}
    out = {}
    for c in ("enrollments", "module_completions", "attainments", "awards", "attempts"):
        out[c] = sorted(json.dumps({k: v for k, v in d.items() if k != "_id"}, sort_keys=True, default=str)
                        for d in db[c].find({}) if str(d.get("user_id")) not in qa)
    return out


def main():
    guard()
    st, data = S().req("POST", "/auth/login", {"email": ADMIN[0], "password": ADMIN[1]})
    admin = S(data["access_token"])
    log("0", "connexion admin du clone (8002)", http=st)

    # qa-e2e-C completes M-001 v1 BEFORE publication
    c, cid = register("c")
    log("7a", "qa-e2e-C inscrit P-001 (avant publication)", http=c.req("POST", "/pathways/P-001/enroll")[0])
    for rid in ("A-001", "A-002"):
        st, prog = c.req("POST", f"/learners/me/resources/{rid}/complete")
    comp = db.module_completions.find_one({"user_id": cid, "module_id": "M-001"}, {"_id": 0})
    enr = db.enrollments.find_one({"user_id": cid}, {"_id": 0, "pathway_id": 1, "pathway_version": 1})
    log("7a", "qa-e2e-C termine M-001 v1 avant publication", http=st, module_status=prog.get("status"), completion=comp, enrollment=enr)
    before_others = others_snapshot()

    # 1. Publication checks
    st, data = admin.req("POST", "/admin/versions/course/CO-001/review", {"decision": "approve", "comment": "E2E clone"})
    st2, data2 = admin.req("POST", "/admin/versions/course/CO-001/publish")
    log("1", "contrôle réel : publication hors ordre de CO-001 v2", http_approve=st, http_publish=st2, detail=data2.get("detail") if isinstance(data2, dict) else None)
    for t, eid in ORDER:
        if (t, eid) != ("course", "CO-001"):
            sa, da = admin.req("POST", f"/admin/versions/{t}/{eid}/review", {"decision": "approve", "comment": "E2E clone"})
        else:
            sa, da = 200, None
        sp, dp = admin.req("POST", f"/admin/versions/{t}/{eid}/publish")
        ent = db[{"question": "question_bank", "assessment": "assessments", "module": "modules", "course": "courses", "pathway": "pathways"}[t]].find_one({"_id": eid})
        log("1", f"approuver + publier {t} {eid}", http_approve=sa, http_publish=sp, refus=dp.get("detail") if isinstance(dp, dict) and sp != 200 else None,
            published_version=(ent or {}).get("published_version"))

    # 2. Learner A, no condition met
    a, aid_ = register("a")
    st, data = a.req("POST", "/credentials/CERT-DOC-01/claim")
    _, creds = a.req("GET", "/learners/me/credentials")
    cert = next(x for x in creds if x["credential"]["id"] == "CERT-DOC-01")
    rules = [(r["id"], r["label"], r["met"]) for r in cert["rules"]]
    log("2", "qa-e2e-A réclame CERT-DOC-01 sans condition", http=st, detail=data.get("detail"), conditions=rules)

    # 3. Read resources, fail graded quiz 3/5 with Q3 partially checked
    for rid in ("A-001", "A-002"):
        a.req("POST", f"/learners/me/resources/{rid}/complete")
    ans = {f"Q-M-001-G{i}": correct(f"Q-M-001-G{i}") for i in range(1, 6)}
    fail = {**ans, "Q-M-001-G3": ans["Q-M-001-G3"][:2], "Q-M-001-G5": ["a"]}
    st, r1 = a.req("POST", "/assessments/A-M-001-G/attempts", {"answers": fail})
    q3 = next(d for d in r1["details"] if d["question_id"] == "Q-M-001-G3")
    k1 = db.attainments.find_one({"user_id": aid_, "competency_id": "K-001"})
    st_c, dc = a.req("POST", "/credentials/CERT-DOC-01/claim")
    log("3", "tentative 1 (Q3 partiellement cochée, Q5 fausse)", http=st, score=f"{r1['attempt']['score']}/{r1['attempt']['max_score']}",
        percent=r1["attempt"]["percent"], passed=r1["attempt"]["passed"], per_competency=r1["attempt"]["per_competency"],
        q3=dict(given=q3["given"], expected=q3["correct_option_ids"], correct=q3["correct"]), k001=bool(k1),
        module_status=r1["module_progress"].get("status"), claim_http=st_c, claim_detail=dc.get("detail"))

    # 4. Pass 4/5 (Q3 wrong), then 5/5
    pass4 = {**ans, "Q-M-001-G3": ans["Q-M-001-G3"][:2]}
    st, r2 = a.req("POST", "/assessments/A-M-001-G/attempts", {"answers": pass4})
    k1 = db.attainments.find_one({"user_id": aid_, "competency_id": "K-001"}, {"_id": 0, "level": 1, "score_percent": 1, "module_id": 1, "status": 1})
    mc = db.module_completions.find_one({"user_id": aid_, "module_id": "M-001"}, {"_id": 0})
    st_c, dc = a.req("POST", "/credentials/CERT-DOC-01/claim")
    log("4", "tentative 2 (4/5, Q3 fausse)", http=st, score=f"{r2['attempt']['score']}/{r2['attempt']['max_score']}", percent=r2["attempt"]["percent"],
        passed=r2["attempt"]["passed"], per_competency=r2["attempt"]["per_competency"], k001=k1, module_status=r2["module_progress"].get("status"),
        completion=mc, claim_http=st_c, claim_detail=dc.get("detail"))
    st, r3 = a.req("POST", "/assessments/A-M-001-G/attempts", {"answers": ans})
    k1 = db.attainments.find_one({"user_id": aid_, "competency_id": "K-001"}, {"_id": 0, "level": 1, "score_percent": 1, "status": 1})
    log("4", "tentative 3 (5/5)", http=st, score=f"{r3['attempt']['score']}/{r3['attempt']['max_score']}", passed=r3["attempt"]["passed"], k001=k1,
        status=r3["status"])
    st, r4 = a.req("POST", "/assessments/A-M-001-G/attempts", {"answers": ans})
    log("5", "4e tentative A-M-001-G", http=st, detail=r4.get("detail"))

    # 5. A-M-003-G then claim
    av = db.assessments.find_one({"_id": "A-M-003-G"})
    qids = [q["question_id"] for q in av["questions"]]
    st, r5 = a.req("POST", "/assessments/A-M-003-G/attempts", {"answers": {q: correct(q) for q in qids}})
    atts = list(db.attainments.find({"user_id": aid_}, {"_id": 0, "competency_id": 1, "level": 1, "score_percent": 1, "module_id": 1}))
    st_c, award = a.req("POST", "/credentials/CERT-DOC-01/claim")
    log("5", "A-M-003-G réussi puis réclamation", http=st, score=f"{r5['attempt']['score']}/{r5['attempt']['max_score']}", passed=r5["attempt"]["passed"],
        attainments=atts, claim_http=st_c, code=award.get("code"), status=award.get("status"), verification_url=award.get("verification_url"),
        evidence=[(e["rule_id"], e.get("module_id"), e.get("score_percent")) for e in award.get("evidence_refs", [])])
    code = award["code"]

    # 6. PDF access, verification, revocation
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
    log("6", "vérification publique sur 8002", http=st, status=v.get("status"))
    st, rv = admin.req("POST", f"/admin/certificates/{code}/revoke", {"reason": "E2E clone : test de révocation"})
    _, v = S().req("GET", f"/verify/{code}")
    st_pdf, _ = a.req("GET", f"/certificates/{code}/pdf")
    log("6", "révocation par l'admin du clone", http=st, status=rv.get("status"), verify_status=v.get("status"), revoke_reason=v.get("revoke_reason"), holder_pdf_http=st_pdf)
    st_re, re_ = a.req("POST", "/credentials/CERT-DOC-01/claim")
    _, v = S().req("GET", f"/verify/{code}")
    k_after = list(db.attainments.find({"user_id": aid_}, {"_id": 0, "competency_id": 1, "status": 1}))
    log("6", "après révocation : nouvelle réclamation et statut de l'ancien code", claim_http=st_re, new_code=re_.get("code") if isinstance(re_, dict) else None,
        claim_detail=re_.get("detail") if isinstance(re_, dict) else None, old_code_status=v.get("status"), attainments=k_after)

    # 7. Existing learners and qa-e2e-C
    after_others = others_snapshot()
    diffs = {k: (len(before_others[k]), len(after_others[k]), before_others[k] == after_others[k]) for k in before_others}
    log("7", "apprenants existants du clone (+ qa-e2e-C) : avant/après publication", identiques=diffs)
    st, prog = c.req("GET", "/learners/me/modules/M-001/progress")
    _, cprog = c.req("GET", "/learners/me/pathways/P-001/progress")
    st_c, dc = c.req("POST", "/credentials/CERT-DOC-01/claim")
    log("7", "qa-e2e-C après publication", http=st, status=prog.get("status"), module_version=prog.get("module_version"), previous_completion=prog.get("previous_completion"),
        k001=db.attainments.count_documents({"user_id": cid}), awards=db.awards.count_documents({"user_id": cid}), claim_http=st_c, claim_detail=dc.get("detail"),
        enrollment=db.enrollments.find_one({"user_id": cid}, {"_id": 0, "pathway_version": 1}),
        pathway_courses=courses_of(cprog))

    # 8. New enrollee on P-001 v2
    dd, did = register("d")
    st, _ = dd.req("POST", "/pathways/P-001/enroll")
    _, dprog = dd.req("GET", "/learners/me/pathways/P-001/progress")
    log("8", "nouvel inscrit qa-e2e-D sur P-001", http=st, enrollment=db.enrollments.find_one({"user_id": did}, {"_id": 0, "pathway_version": 1}),
        pathway_courses=courses_of(dprog))

    (D / "scenario_report.json").write_text(json.dumps(REPORT, ensure_ascii=False, indent=1, default=str))
    os.chmod(D / "scenario_report.json", 0o600)


if __name__ == "__main__":
    main()
