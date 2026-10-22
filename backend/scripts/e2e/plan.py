"""Isolated test plan (rules 2026-10) — ONLY against casa_e2e_plan served on 127.0.0.1:8002. Usage: plan.py 1|2|3"""
import hashlib
import io
import json
import os
import re
import secrets
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from pymongo import MongoClient
from pypdf import PdfReader

sys.path.insert(0, "/app/backend/tests")
from creds import ADMIN  # noqa: E402

load_dotenv("/app/backend/.env", override=False)
E2E, BASE, D = "casa_e2e_plan", "http://127.0.0.1:8002/api", Path("/app/backups/e2e")
db = MongoClient(os.environ["MONGO_URL"])[E2E]
STATE, LOG = D / "plan_state.json", D / "plan_report.json"
TYPES = {"Ressource": "resource", "Question": "question", "Évaluation": "assessment", "Module": "module", "Cours": "course", "Parcours": "pathway"}


def guard(flags=None):
    pid = (D / "8002.pid").read_text().strip()
    env = dict(x.split("=", 1) for x in Path(f"/proc/{pid}/environ").read_bytes().decode().split("\0") if "=" in x)
    cmd = Path(f"/proc/{pid}/cmdline").read_bytes().decode().split("\0")
    if env.get("DB_NAME") != E2E or env.get("CASA_TEST_DB") != E2E or cmd[cmd.index("--port") + 1] != "8002":
        sys.exit("ARRÊT : la cible n'est pas casa_e2e_plan sur le port 8002")
    return env.get("CASA_LEVEL_FROM_ASSESSMENT_MODULE_VERSION"), env.get("CASA_EXTRA_ATTEMPT_GRANTS")


def call(method, path, tok=None, body=None):
    if method != "GET":
        guard()
    r = requests.request(method, BASE + path, json=body, headers={"Authorization": f"Bearer {tok}"} if tok else {}, timeout=60)
    return r.status_code, (r.json() if "json" in r.headers.get("content-type", "") else r.content)


def log(step, label, **kw):
    rep = json.loads(LOG.read_text()) if LOG.exists() else []
    rep.append({"step": step, "label": label, **kw})
    LOG.write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str))
    os.chmod(LOG, 0o600)
    print(f"[{step}] {label} :: " + json.dumps(kw, ensure_ascii=False, default=str)[:700])


def state():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save(st):
    STATE.write_text(json.dumps(st))
    os.chmod(STATE, 0o600)


def login(email, pw):
    st, d = call("POST", "/auth/login", body={"email": email, "password": pw})
    assert st == 200, (email, st, d)
    return d["access_token"]


def learner(st, tag):
    if tag not in st:
        pw = "Qa-" + secrets.token_urlsafe(12)
        email = f"qa-e2e-plan-{tag}@example.com"
        s, d = call("POST", "/auth/register", body={"first_name": "QA", "last_name": f"Plan {tag.upper()}", "email": email, "password": pw})
        assert s == 200, d
        st[tag] = {"email": email, "password": pw, "id": d["user"]["id"]}
        save(st)
    return login(st[tag]["email"], st[tag]["password"]), st[tag]["id"]


def answers(aid, wrong=()):
    ent = db.assessments.find_one({"_id": aid})
    v = db.assessment_versions.find_one({"entity_id": aid, "version": ent["published_version"]})
    out = {}
    for i, q in enumerate(v["questions"]):
        corr = db.questions.find_one({"_id": f"{q['question_id']}@{q['version']}"})["correct"]
        out[q["question_id"]] = ["zz"] if i in wrong else corr
    return out


def attempt(tok, aid, wrong=()):
    s, r = call("POST", f"/assessments/{aid}/attempts", tok, {"answers": answers(aid, wrong)})
    if s != 200:
        return s, r.get("detail"), None
    a = r["attempt"]
    return s, {k: a.get(k) for k in ("attempt_number", "assessment_version", "module_version", "level_evaluated", "score", "max_score", "passed")}, r


def atts(uid, comp=None):
    q = {"user_id": uid, **({"competency_id": comp} if comp else {})}
    return [{k: a.get(k) for k in ("competency_id", "module_id", "level", "score_percent")} | {"mv": a["evidence"].get("module_version"), "lv": a["evidence"].get("level_evaluated")}
            for a in db.attainments.find(q)]


def h(docs):
    return hashlib.sha256(json.dumps(sorted(json.dumps(d, sort_keys=True, default=str) for d in docs)).encode()).hexdigest()[:16]


def approve_publish(adm, t, eid):
    call("POST", f"/admin/versions/{t}/{eid}/review", adm, {"decision": "approve", "comment": "E2E plan (clone)"})
    return call("POST", f"/admin/versions/{t}/{eid}/publish", adm)


def phase1():
    print("interrupteurs :", guard())
    st = state()
    adm = login(*ADMIN)
    st["m01_existing"] = h(db.attempts.find({"assessment_id": "A-M01-G"}, {"_id": 0}))
    save(st)
    a, aid_ = learner(st, "a")
    call("POST", "/pathways/P-001/enroll", a)
    for rid in ("A-001", "A-002"):
        call("POST", f"/learners/me/resources/{rid}/complete", a)
    log("a", "avant publication : P-001 v1, M-001 v1 terminé", enrollment=db.enrollments.find_one({"user_id": aid_}, {"_id": 0, "pathway_version": 1}),
        completion=db.module_completions.find_one({"user_id": aid_, "module_id": "M-001"}, {"_id": 0, "module_version": 1}))
    b, bid = learner(st, "b")
    res = [attempt(b, "A-M-003-G", wrong=(0, 1, 2))[1] for _ in range(3)]
    log("b", "avant publication : 3 tentatives échouées sur A-M-003-G v1", attempts=res)
    st["b_first3"] = h(db.attempts.find({"user_id": bid}, {"_id": 0}))
    e, eid = learner(st, "e")
    log("e", "avant publication : A-M-003-G v1 réussi", attempt=attempt(e, "A-M-003-G")[1], attainments=atts(eid))
    m, mid = learner(st, "m01")
    log("f", "avant publication : 2 tentatives sur A-M01-G v1", attempts=[attempt(m, "A-M01-G", wrong=(0, 1, 2, 3))[1] for _ in range(2)])
    save(st)
    # (g) refusals
    s, d = approve_publish(adm, "assessment", "A-M-003-G")
    log("g", "A-M-003-G v2 publié trop tôt", http=s, detail=d.get("detail"))
    v = db.assessment_versions.find_one({"entity_id": "A-M-003-G", "version": 2})
    c = {k: v[k] for k in ("kind", "module_id", "pass_threshold", "max_attempts")} | {"code": "A-E2E-NOMV", "title": "QA E2E sans module_version",
                                                                                         "questions": [{"question_id": "Q-M-003-G2", "version": 1}]}
    log("g", "création évaluation de test sans module_version", http=call("POST", "/admin/content/assessment", adm, {"id": "A-E2E-NOMV", "content": c, "changelog": "E2E"})[0])
    call("POST", "/admin/versions/assessment/A-E2E-NOMV/submit", adm)
    s, d = approve_publish(adm, "assessment", "A-E2E-NOMV")
    log("g", "publication sans module_version", http=s, detail=d.get("detail"))
    # publication of the export's queue
    _, md = call("GET", "/admin/review-queue/export?format=md", adm)
    order = re.findall(r"^\d+\. (\S+) (\S+) v(\d+)$", md.decode().split("## Ordre de publication")[1].split("##")[0], re.M)
    out = []
    for label, eid_, ver in order:
        s, d = approve_publish(adm, TYPES[label], eid_)
        out.append((eid_, int(ver), s, None if s == 200 else d.get("detail")))
    log("1", f"publication des {len(order)} éléments dans l'ordre de l'export", resultats=out)
    s, prog = call("GET", "/learners/me/modules/M-001/progress", a)
    _, pp = call("GET", "/learners/me/pathways/P-001/progress", a)
    log("a", "après publication", module_version=prog.get("module_version"), status=prog.get("status"), previous_completion=prog.get("previous_completion"),
        pathway_version=pp.get("pathway_version"), courses=[(c["course_id"], c["course_version"], [(x["module_id"], x["module_version"]) for x in c["modules"]]) for g in pp["groups"].values() for c in g])
    s, d = attempt(b, "A-M-003-G", wrong=(0, 1, 2))[:2]
    log("b", "4e tentative sans octroi", http=s, detail=d)
    log("b", "octroi sans motif", http=call("POST", "/admin/attempt-grants", adm, {"email": st["b"]["email"], "assessment_id": "A-M-003-G", "reason": ""})[0])
    log("b", "octroi à l'admin lui-même", http=(r := call("POST", "/admin/attempt-grants", adm, {"email": ADMIN[0], "assessment_id": "A-M-003-G", "reason": "test"}))[0], detail=r[1].get("detail"))
    s, g = call("POST", "/admin/attempt-grants", adm, {"email": st["b"]["email"], "assessment_id": "A-M-003-G", "reason": "QA E2E : 3 tentatives épuisées avant la v2"})
    _, ass = call("GET", "/assessments/A-M-003-G", b)
    log("b", "octroi par l'admin", http=s, journal=bool(db.catalog_change_log.find_one({"action": "grant", "details": "QA E2E : 3 tentatives épuisées avant la v2"})), status=ass["status"])


def phase2():
    print("interrupteurs :", guard())
    st, adm = state(), login(*ADMIN)
    a, aid_ = login(st["a"]["email"], st["a"]["password"]), st["a"]["id"]
    log("a", "réussite A-M-001-G", attempt=attempt(a, "A-M-001-G")[1], k001=atts(aid_, "K-001"))
    b, bid = login(st["b"]["email"], st["b"]["password"]), st["b"]["id"]
    s, d, _ = attempt(b, "A-M-003-G", wrong=(0, 1, 2))
    g = db.attempt_grants.find_one({"user_id": bid}, sort=[("granted_at", 1)])
    log("b", "4e tentative avec octroi (échouée)", http=s, attempt=d, grant_consumed=bool(g["consumed_at"]), grant_attempt_id=bool(g["attempt_id"]),
        first3_unchanged=h(db.attempts.find({"user_id": bid, "attempt_number": {"$lte": 3}}, {"_id": 0})) == st["b_first3"])
    s, d = attempt(b, "A-M-003-G")[:2]
    log("b", "5e tentative sans nouvel octroi", http=s, detail=d)
    call("POST", "/admin/attempt-grants", adm, {"email": st["b"]["email"], "assessment_id": "A-M-003-G", "reason": "QA E2E : second octroi"})
    log("b", "5e tentative avec second octroi", attempt=attempt(b, "A-M-003-G")[1])
    s, d = call("POST", "/admin/attempt-grants", adm, {"email": st["b"]["email"], "assessment_id": "A-M-003-G", "reason": "QA E2E : après réussite"})
    log("b", "octroi après réussite", http=s, detail=d.get("detail"), attempts_total=db.attempts.count_documents({"user_id": bid}))
    # (c) full path
    c, cid = learner(st, "c")
    s, _ = call("POST", "/pathways/P-001/enroll", c)
    for rid in ("A-001", "A-002"):
        call("POST", f"/learners/me/resources/{rid}/complete", c)
    r1, r2 = attempt(c, "A-M-001-G")[1], attempt(c, "A-M-003-G")[1]
    s, award = call("POST", "/credentials/CERT-DOC-01/claim", c)
    code = award["code"]
    o, _ = learner(st, "other")
    pdf = {w: call("GET", f"/certificates/{code}/pdf", t)[0] for w, t in (("titulaire", c), ("admin", adm), ("autre", o), ("visiteur", None))}
    body = call("GET", f"/certificates/{code}/pdf", c)[1]
    txt = "".join(p.extract_text() for p in PdfReader(io.BytesIO(body)).pages)
    log("c", "parcours complet P-001 v2", enrollment=db.enrollments.find_one({"user_id": cid}, {"_id": 0, "pathway_version": 1}), a_m001=r1, a_m003=r2,
        claim=s, code=code, attainments=atts(cid), pdf=pdf, mention_clone="CLONE E2E — sans valeur" in txt, url_locale=f"localhost:8002/verifier/{code}" in txt,
        verify=call("GET", f"/verify/{code}")[1].get("status"))
    call("POST", f"/admin/certificates/{code}/revoke", adm, {"reason": "QA E2E plan : révocation"})
    s1, d1 = call("POST", "/credentials/CERT-DOC-01/claim", c)
    s2, _ = call("POST", f"/admin/certificates/{code}/allow-reclaim", adm, {"reason": "QA E2E plan : autorisation"})
    s3, d3 = call("POST", "/credentials/CERT-DOC-01/claim", c)
    s4, d4 = call("POST", f"/admin/certificates/{d3.get('code')}/revoke", adm, {"reason": "QA E2E plan : 2e révocation"})
    log("c", "révocation, blocage, autorisation unique", verify_old=call("GET", f"/verify/{code}")[1].get("status"), claim_blocked=(s1, d1.get("detail")),
        allow=s2, claim_after_allow=(s3, d3.get("status")), claim_after_second_revoke=call("POST", "/credentials/CERT-DOC-01/claim", c)[0])
    # (d)
    dd, did = learner(st, "d")
    log("d", "A-M-003-G v2 seul", attempt=attempt(dd, "A-M-003-G")[1], attainments=atts(did), claim=call("POST", "/credentials/CERT-DOC-01/claim", dd)[0])
    # (e) non-retroactivity
    e_before = atts(st["e"]["id"])
    v1 = db.module_versions.find_one({"entity_id": "M-003", "version": 1})
    mc = {k: v1[k] for k in v1 if k not in ("_id", "entity_id", "version", "status", "approved", "changelog", "created_at", "created_by", "updated_at", "updated_by",
                                            "submitted_at", "submitted_by", "reviews", "published_at", "published_by", "superseded")} | {"levels": ["L1", "L2"]}
    call("PUT", "/admin/content/module/M-003", adm, {"content": mc, "changelog": "E2E plan : version de test M-003 v2 en L2 (clone uniquement)"})
    call("POST", "/admin/versions/module/M-003/submit", adm)
    s, d = approve_publish(adm, "module", "M-003")
    f, fid = learner(st, "f")
    log("e", "M-003 v2 (L2, test) publiée", http=s, e_avant=e_before, e_apres=atts(st["e"]["id"]), nouvel_apprenant=attempt(f, "A-M-003-G")[1], f_attainments=atts(fid))
    # (f) M01
    m, mid = login(st["m01"]["email"], st["m01"]["password"]), st["m01"]["id"]
    _, ass = call("GET", "/assessments/A-M01-G", m)
    log("f", "M01 après publication de A-M01-G v2", version=ass.get("version"), status=ass["status"],
        existing_attempts_unchanged=h(db.attempts.find({"assessment_id": "A-M01-G", "user_id": {"$nin": [mid]}}, {"_id": 0})) == st["m01_existing"],
        third=attempt(m, "A-M01-G")[1], fourth=attempt(m, "A-M01-G")[:2])
    save(st)


def phase3():
    flags = guard()
    st, adm = state(), login(*ADMIN)
    g, gid = learner(st, "h")
    b = login(st["b"]["email"], st["b"]["password"])
    s, d, _ = attempt(g, "A-M-003-G")
    log("h", "interrupteurs désactivés sur le clone", flags=flags, attempt=d, attainments=atts(gid), grants_api=call("GET", "/admin/attempt-grants", adm)[0],
        b_status=call("GET", "/assessments/A-M-003-G", b)[1]["status"], b_new_attempt=attempt(b, "A-M-003-G")[0])
    s, d = call("POST", "/admin/versions/assessment/A-E2E-NOMV/publish", adm)
    log("h", "publication sans module_version, interrupteur désactivé", http=s, detail=d.get("detail") if isinstance(d, dict) and s != 200 else None)


{"1": phase1, "2": phase2, "3": phase3}[sys.argv[1]]()
