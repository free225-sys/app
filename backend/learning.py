from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import User, get_current_user, get_optional_user
from core import BaseDocument, LEVEL_ORDER, all_docs, db, now_iso, pinned, published, versions_by_key

router = APIRouter(prefix="/api", tags=["learning"])

PUBLIC_Q_FIELDS = ["question_id", "type", "prompt", "options", "competencies"]
ATTAIN_THRESHOLD = 0.7


class AttemptIn(BaseModel):
    answers: Dict[str, List[str]] = Field(default_factory=dict)


class CheckIn(BaseModel):
    question_id: str
    answer: List[str]


class DemoProgressIn(BaseModel):
    scenario_id: str = "casa-jo-cafe-cacao"
    max_step: int = Field(ge=1, le=7)
    quiz_answers: Dict[str, int] = Field(default_factory=dict)


async def create_indexes():
    await db.resource_progress.create_index([("user_id", 1), ("resource_id", 1)], unique=True)
    await db.attempts.create_index([("user_id", 1), ("assessment_id", 1)])
    await db.attainments.update_many({"evidence_type": {"$exists": False}}, {"$set": {"evidence_type": "graded_attempt", "status": "valid"}})
    await dedupe_attainments()
    if "user_id_1_competency_id_1_module_id_1" in await db.attainments.index_information():
        await db.attainments.drop_index("user_id_1_competency_id_1_module_id_1")
    await db.attainments.create_index([("user_id", 1), ("competency_id", 1), ("module_id", 1), ("evidence_type", 1)], unique=True)
    await db.module_completions.update_many({"module_version": {"$exists": False}}, {"$set": {"module_version": 1}})
    await db.module_completions.create_index([("user_id", 1), ("module_id", 1)], unique=True)
    await db.demo_progress.create_index([("user_id", 1), ("scenario_id", 1)], unique=True)


async def dedupe_attainments():
    pipe = [{"$group": {"_id": {"u": "$user_id", "c": "$competency_id", "m": "$module_id", "e": "$evidence_type"}, "docs": {"$push": {"id": "$_id", "status": "$status", "score": "$score_percent"}}, "n": {"$sum": 1}}},
            {"$match": {"n": {"$gt": 1}}}]
    async for g in db.attainments.aggregate(pipe):
        keep = sorted(g["docs"], key=lambda d: (d.get("status") == "valid", d.get("score") or 0), reverse=True)[0]
        await db.attainments.delete_many({"_id": {"$in": [d["id"] for d in g["docs"] if d["id"] != keep["id"]]}})


# ---------- Assessments ----------
async def load_assessment(aid: str):
    ent = await db.assessments.find_one({"_id": aid})
    ver = ent and await db.assessment_versions.find_one({"entity_id": aid, "version": ent.get("published_version"), "status": "published"})
    if not ver:
        raise HTTPException(404, "Évaluation introuvable")
    ids = [f"{r['question_id']}@{r['version']}" for r in ver["questions"]]
    docs = {d["_id"]: d for d in await db.questions.find({"_id": {"$in": ids}}).to_list(500)}
    return BaseDocument.from_mongo(ent).out(), ver["version"], [docs[i] for i in ids if i in docs]


def public_question(q: dict) -> dict:
    return {k: q[k] for k in PUBLIC_Q_FIELDS if k in q}


def assessment_meta(ent: dict, version: int, questions: list) -> dict:
    return {"id": ent["id"], "kind": ent["kind"], "module_id": ent["module_id"], "title": ent["title"], "version": version,
            "pass_threshold": ent["pass_threshold"], "max_attempts": ent["max_attempts"], "question_count": len(questions)}


async def user_attempts(user_id: str, aid: Optional[str] = None) -> List[dict]:
    query = {"user_id": user_id, **({"assessment_id": aid} if aid else {})}
    docs = await db.attempts.find(query).sort("created_at", 1).to_list(1000)
    return [BaseDocument.from_mongo(d).out() for d in docs]


def attempt_status(ent: dict, attempts: List[dict]) -> dict:
    used = len(attempts)
    return {"attempts_used": used, "max_attempts": ent["max_attempts"], "remaining": max(ent["max_attempts"] - used, 0),
            "best_percent": max((a["percent"] for a in attempts), default=None), "passed": any(a["passed"] for a in attempts)}


@router.get("/modules/{module_id}/assessments")
async def module_assessments(module_id: str):
    out = []
    for kind in ["F", "G"]:
        ent = await db.assessments.find_one({"_id": f"A-{module_id}-{kind}"})
        if ent:
            e, version, qs = await load_assessment(ent["_id"])
            out.append(assessment_meta(e, version, qs))
    return out


@router.get("/assessments/{aid}")
async def get_assessment(aid: str, user: Optional[User] = Depends(get_optional_user)):
    ent, version, qs = await load_assessment(aid)
    if ent["kind"] == "graded" and not user:
        raise HTTPException(401, "Connexion requise pour accéder à l'évaluation notée.")
    data = assessment_meta(ent, version, qs)
    data["questions"] = [public_question(q) for q in qs]
    if user and ent["kind"] == "graded":
        data["status"] = attempt_status(ent, await user_attempts(user.id, aid))
    return data


@router.post("/assessments/{aid}/check")
async def check_answer(aid: str, body: CheckIn):
    ent, _, qs = await load_assessment(aid)
    if ent["kind"] != "formative":
        raise HTTPException(403, "La correction immédiate n'est disponible que pour les quiz formatifs.")
    q = next((q for q in qs if q["question_id"] == body.question_id), None)
    if not q:
        raise HTTPException(404, "Question introuvable")
    return {"question_id": q["question_id"], "correct": sorted(body.answer) == sorted(q["correct"]),
            "correct_option_ids": q["correct"], "explanation": q["explanation"]}


def score_attempt(qs: List[dict], answers: Dict[str, List[str]]):
    per_comp, details, correct_count = {}, [], 0
    for q in qs:
        ok = sorted(answers.get(q["question_id"], [])) == sorted(q["correct"])
        correct_count += ok
        for c in q["competencies"]:
            agg = per_comp.setdefault(c["competency_id"], {"competency_id": c["competency_id"], "score": 0, "max": 0})
            agg["max"] += c["weight"]
            agg["score"] += c["weight"] if ok else 0
        details.append({"question_id": q["question_id"], "correct": ok, "given": answers.get(q["question_id"], []),
                        "correct_option_ids": q["correct"], "explanation": q["explanation"]})
    for agg in per_comp.values():
        agg["percent"] = round(agg["score"] / agg["max"], 4) if agg["max"] else 0
    return correct_count, list(per_comp.values()), details


async def module_level(module_id: str) -> str:
    ent = await db.modules.find_one({"_id": module_id})
    ver = await db.module_versions.find_one({"entity_id": module_id, "version": ent["published_version"]})
    return sorted(ver["levels"], key=LEVEL_ORDER.index)[-1]


async def record_attainments(user: User, attempt: dict):
    level = await module_level(attempt["module_id"])
    for comp in attempt["per_competency"]:
        if comp["percent"] < ATTAIN_THRESHOLD:
            continue
        key = {"user_id": user.id, "competency_id": comp["competency_id"], "module_id": attempt["module_id"], "evidence_type": "graded_attempt"}
        existing = await db.attainments.find_one(key)
        if existing and existing.get("status") == "valid" and existing["score_percent"] >= comp["percent"]:
            continue
        await db.attainments.update_one(key, {"$set": {
            **key, "level": level, "score_percent": comp["percent"], "acquired_at": attempt["created_at"], "status": "valid",
            "evidence": {"type": "graded_attempt", "attempt_id": attempt["id"], "assessment_id": attempt["assessment_id"],
                         "assessment_version": attempt["assessment_version"], "attempt_number": attempt["attempt_number"],
                         "attempt_percent": attempt["percent"]}}}, upsert=True)


@router.post("/assessments/{aid}/attempts")
async def submit_attempt(aid: str, body: AttemptIn, user: User = Depends(get_current_user)):
    ent, version, qs = await load_assessment(aid)
    if ent["kind"] != "graded":
        raise HTTPException(400, "Seules les évaluations notées acceptent des tentatives.")
    previous = await user_attempts(user.id, aid)
    if len(previous) >= ent["max_attempts"]:
        raise HTTPException(403, f"Nombre maximal de tentatives atteint ({ent['max_attempts']}).")
    correct_count, per_comp, details = score_attempt(qs, body.answers)
    percent = round(correct_count / len(qs), 4)
    attempt = {"user_id": user.id, "assessment_id": aid, "assessment_version": version, "module_id": ent["module_id"],
               "kind": "graded", "attempt_number": len(previous) + 1, "answers": body.answers, "score": correct_count,
               "max_score": len(qs), "percent": percent, "passed": percent >= ent["pass_threshold"],
               "per_competency": per_comp, "created_at": now_iso()}
    res = await db.attempts.insert_one(attempt)
    attempt["id"] = str(res.inserted_id)
    attempt.pop("_id", None)
    if attempt["passed"]:
        await record_attainments(user, attempt)
    module = await module_progress(user.id, ent["module_id"])
    status = attempt_status(ent, previous + [attempt])
    return {"attempt": attempt, "details": details, "status": status, "module_progress": module}


@router.get("/assessments/{aid}/attempts")
async def list_attempts(aid: str, user: User = Depends(get_current_user)):
    return await user_attempts(user.id, aid)


# ---------- Diagnostic ----------
@router.get("/diagnostic")
async def get_diagnostic():
    ent, version, qs = await load_assessment("A-DIAG")
    return {**assessment_meta(ent, version, qs), "questions": [public_question(q) for q in qs]}


@router.post("/diagnostic/submit")
async def submit_diagnostic(body: AttemptIn, user: Optional[User] = Depends(get_optional_user)):
    _, version, qs = await load_assessment("A-DIAG")
    votes, knowledge, knowledge_max = {}, 0, 0
    for q in qs:
        given = (body.answers.get(q["question_id"]) or [None])[0]
        if q["diagnostic_kind"] == "profile":
            if given in q["option_values"]:
                pid = q["option_values"][given]
                votes[pid] = votes.get(pid, 0) + q["weight"]
        else:
            knowledge_max += 1
            knowledge += given in q["correct"]
    profiles = {p["id"]: p for p in await all_docs("profiles")}
    profile_id = max(votes, key=votes.get) if votes else "profile-decouvrir"
    profile = profiles[profile_id]
    level = "L0" if knowledge <= 2 else "L1" if knowledge <= 4 else "L2"
    course_id = profile["course_ids"][0]
    preparatory = "C01" if knowledge <= 2 and profile_id in ("profile-concevoir", "profile-piloter") else None
    message = f"Entrée recommandée : {profile['name']} ({profile['audience']})."
    if preparatory:
        message += " Nous vous conseillons de commencer par le cours C01 « Découvrir l'IA » pour consolider les bases."
    result = {"profile_id": profile_id, "profile_name": profile["name"], "course_id": course_id, "preparatory_course_id": preparatory,
              "knowledge_score": knowledge, "knowledge_max": knowledge_max, "estimated_level": level, "message": message,
              "assessment_version": version, "saved": bool(user)}
    if user:
        await db.diagnostic_results.insert_one({"user_id": user.id, "answers": body.answers, **result, "created_at": now_iso()})
    return result


# ---------- Progress ----------
async def modules_by_id() -> Dict[str, dict]:
    return {m["id"]: m for m in await published("modules", "module_versions")}


async def module_index() -> Dict[str, dict]:
    return {**await modules_by_id(), **await versions_by_key("module_versions")}


def compute_module_progress(mod: dict, done: set, attempts: List[dict], resources: Dict[str, dict]) -> dict:
    rids = mod["resource_ids"]
    done_count = sum(r in done for r in rids)
    by_resources = mod.get("completion_rule") == "resources"
    passed = any(a["passed"] for a in attempts) or (by_resources and done_count == len(rids))
    completed = done_count == len(rids) and passed
    started = done_count > 0 or attempts
    status = "completed" if completed else "in_progress" if started else "not_started"
    next_rid = next((r for r in rids if r not in done), None)
    return {"module_id": mod["id"], "code": mod["code"], "title": mod["title"], "status": status, "module_version": mod["version"],
            "percent": round(done_count / len(rids), 4) if by_resources and rids else round((done_count + (1 if passed else 0)) / (len(rids) + 1), 4),
            "resources_done": done_count, "resources_total": len(rids),
            "resources": [{"id": r, "title": resources.get(r, {}).get("title"), "type": resources.get(r, {}).get("type"),
                           "completed": r in done} for r in rids],
            "graded": None if by_resources else {"assessment_id": f"A-{mod['id']}-G", "attempts_used": len(attempts),
                                                 "best_percent": max((a["percent"] for a in attempts), default=None), "passed": passed},
            "next_resource_id": next_rid}


async def user_state(user_id: str):
    done = {d["resource_id"] for d in await db.resource_progress.find({"user_id": user_id}).to_list(5000)}
    attempts = await user_attempts(user_id)
    by_module = {}
    for a in attempts:
        by_module.setdefault(a["module_id"], []).append(a)
    resources = {r["id"]: r for r in await all_docs("resources", "_id")}
    return done, by_module, resources, attempts


async def mark_completion(user_id: str, prog: dict):
    if prog["status"] == "completed":
        await db.module_completions.update_one({"user_id": user_id, "module_id": prog["module_id"]},
                                               {"$setOnInsert": {"completed_at": now_iso(), "module_version": prog["module_version"]}}, upsert=True)


async def module_progress(user_id: str, module_id: str) -> dict:
    mods = await modules_by_id()
    if module_id not in mods:
        raise HTTPException(404, "Module introuvable")
    done, by_module, resources, _ = await user_state(user_id)
    prog = compute_module_progress(mods[module_id], done, by_module.get(module_id, []), resources)
    await mark_completion(user_id, prog)
    return prog


@router.post("/learners/me/resources/{resource_id}/complete")
async def complete_resource(resource_id: str, user: User = Depends(get_current_user)):
    res = await db.resources.find_one({"_id": resource_id})
    if not res:
        raise HTTPException(404, "Ressource introuvable")
    await db.resource_progress.update_one({"user_id": user.id, "resource_id": resource_id},
                                          {"$setOnInsert": {"module_id": res["module_id"], "completed_at": now_iso()}}, upsert=True)
    return await module_progress(user.id, res["module_id"])


@router.get("/learners/me/modules/{module_id}/progress")
async def get_module_progress(module_id: str, user: User = Depends(get_current_user)):
    return await module_progress(user.id, module_id)


def course_progress(course: dict, mods: Dict[str, dict], done, by_module, resources) -> dict:
    pins = course.get("module_pins") or {}
    items = [compute_module_progress(pinned(mods, mid, pins.get(mid)) or mods[mid], done, by_module.get(mid, []), resources)
             for mid in course["module_ids"] if pinned(mods, mid, pins.get(mid)) or mid in mods]
    nxt = next((m for m in items if m["status"] != "completed"), None)
    started = any(m["status"] != "not_started" for m in items)
    return {"course_id": course["id"], "code": course["code"], "title": course["title"],
            "percent": round(sum(m["percent"] for m in items) / len(items), 4) if items else 0,
            "completed_count": sum(m["status"] == "completed" for m in items), "module_count": len(items),
            "status": "completed" if nxt is None else "in_progress" if started else "not_started",
            "modules": items, "resume": {"module_id": nxt["module_id"], "resource_id": nxt["next_resource_id"]} if nxt else None}


@router.get("/learners/me/courses/{course_id}/progress")
async def get_course_progress(course_id: str, user: User = Depends(get_current_user)):
    courses = {c["id"]: c for c in await published("courses", "course_versions")}
    if course_id not in courses:
        raise HTTPException(404, "Cours introuvable")
    done, by_module, resources, _ = await user_state(user.id)
    return course_progress(courses[course_id], await module_index(), done, by_module, resources)


async def attainments_for(user_id: str) -> List[dict]:
    comps = {c["id"]: c for c in await all_docs("competencies")}
    mods = await modules_by_id()
    docs = await db.attainments.find({"user_id": user_id}).sort("acquired_at", -1).to_list(1000)
    out = []
    for d in docs:
        a = BaseDocument.from_mongo(d).out()
        a["competency_name"] = comps.get(a["competency_id"], {}).get("name")
        a["module_title"] = mods.get(a["module_id"], {}).get("title")
        out.append(a)
    return out


@router.get("/learners/me/attainments")
async def get_attainments(user: User = Depends(get_current_user)):
    return await attainments_for(user.id)


@router.post("/learners/me/demo-progress")
async def save_demo_progress(body: DemoProgressIn, user: User = Depends(get_current_user)):
    scenario = await db.demo_scenarios.find_one({"_id": body.scenario_id})
    if not scenario:
        raise HTTPException(404, "Scénario introuvable")
    key = {"user_id": user.id, "scenario_id": body.scenario_id}
    existing = await db.demo_progress.find_one(key) or {}
    max_step = max(body.max_step, existing.get("max_step", 0))
    answers = {**existing.get("quiz_answers", {}), **body.quiz_answers}
    quiz = scenario["quiz"]
    score = sum(1 for q in quiz if answers.get(q["id"]) == q["correct"])
    doc = {**key, "max_step": max_step, "completed": max_step >= len(scenario["steps"]), "quiz_answers": answers,
           "quiz_score": score, "quiz_total": len(quiz), "quiz_done": len(answers) >= len(quiz), "updated_at": now_iso()}
    await db.demo_progress.update_one(key, {"$set": doc}, upsert=True)
    return doc


@router.get("/learners/me/dashboard")
async def dashboard(user: User = Depends(get_current_user)):
    mods = await modules_by_id()
    courses = await published("courses", "course_versions")
    done, by_module, resources, attempts = await user_state(user.id)
    index = await module_index()
    course_list = [course_progress(c, index, done, by_module, resources) for c in courses]
    module_states = {mid: compute_module_progress(m, done, by_module.get(mid, []), resources) for mid, m in mods.items()}
    for p in module_states.values():
        await mark_completion(user.id, p)
    demo = await db.demo_progress.find_one({"user_id": user.id}, {"_id": 0, "user_id": 0})
    diag = await db.diagnostic_results.find_one({"user_id": user.id}, {"_id": 0, "user_id": 0, "answers": 0}, sort=[("created_at", -1)])
    recos = []
    if not demo or not demo.get("completed"):
        recos.append({"kind": "demo", "label": "Terminer la démonstration interactive", "reason": "Elle donne une vue d'ensemble des 7 étapes."})
    target = None
    in_progress = [c for c in course_list if c["status"] == "in_progress"]
    if in_progress:
        target, reason = in_progress[0], "Cours en cours"
    elif diag:
        target, reason = next((c for c in course_list if c["course_id"] == (diag.get("preparatory_course_id") or diag["course_id"])), None), "Recommandé par votre test de positionnement"
    if target and target["resume"]:
        m = mods[target["resume"]["module_id"]]
        recos.append({"kind": "module", "module_id": m["id"], "course_id": target["course_id"], "label": f"{m['code']} — {m['title']}", "reason": f"{reason} : {target['title']}"})
    elif module_states["M01"]["status"] != "completed":
        recos.append({"kind": "module", "module_id": "M01", "label": "M01 — Comprendre les usages, capacités et limites", "reason": "Module gratuit recommandé pour commencer"})
    if not diag:
        recos.append({"kind": "diagnostic", "label": "Passer le test de positionnement", "reason": "Huit questions pour identifier votre point d'entrée."})
    titles = {a: f"{mods[a.split('-')[1]]['code']} — {mods[a.split('-')[1]]['title']}" for a in {x['assessment_id'] for x in attempts}}
    history = [{**{k: a[k] for k in ["id", "assessment_id", "module_id", "attempt_number", "score", "max_score", "percent", "passed", "created_at", "per_competency"]},
                "module_label": titles[a["assessment_id"]]} for a in reversed(attempts)]
    return {"user": user.public(), "courses": course_list,
            "modules_in_progress": [p for p in module_states.values() if p["status"] == "in_progress"],
            "modules_completed": [p for p in module_states.values() if p["status"] == "completed"],
            "attempts": history, "attainments": await attainments_for(user.id), "demo": demo, "diagnostic": diag,
            "recommendations": recos}
