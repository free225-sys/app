from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException

from auth import User, get_current_user, require_learner
from core import EntityVersion, LEVEL_ORDER, db, now_iso, pinned, published, versions_by_key
from learning import course_progress, module_index, modules_by_id, user_state

router = APIRouter(prefix="/api", tags=["pathways"])


def level_ok(level: str, required: str) -> bool:
    return LEVEL_ORDER.index(level) >= LEVEL_ORDER.index(required)


async def pathway_version(pathway_id: str, version: int = None) -> dict:
    ent = await db.pathways.find_one({"_id": pathway_id})
    if not ent:
        raise HTTPException(404, "Parcours introuvable")
    doc = await db.pathway_versions.find_one({"entity_id": pathway_id, "version": version or ent["published_version"]})
    v = EntityVersion.from_mongo(doc).out()
    v["id"] = pathway_id
    return v


async def course_for(pc: dict) -> dict:
    query = {"entity_id": pc["course_id"], "status": {"$in": ["published", "retired"]}}
    if pc.get("course_version"):
        query["version"] = pc["course_version"]
    return await db.course_versions.find_one(query, sort=[("version", -1)])


async def valid_attainments(user_id: str) -> List[dict]:
    return await db.attainments.find({"user_id": user_id, "status": "valid"}).to_list(1000)


async def recognition_snapshot(user_id: str, pv: dict, enrolled_at: str) -> dict:
    mods = await modules_by_id()
    module_ids = {mid for pc in pv["pathway_courses"] for c in [await course_for(pc)] for mid in c["module_ids"]}
    completions = await db.module_completions.find({"user_id": user_id, "module_id": {"$in": list(module_ids)}}).to_list(100)
    recognized_modules = [{"module_id": c["module_id"], "module_version": c["module_version"], "completed_at": c["completed_at"]}
                          for c in completions if c["completed_at"] <= enrolled_at and c["module_version"] == mods[c["module_id"]]["version"]]
    accepted = {t for pc in pv["pathway_courses"] for t in pc["bridge"]["accepted_evidence_types"]}
    atts = await valid_attainments(user_id)
    recognized_comps = []
    for t in pv["target_competencies"]:
        match = next((a for a in sorted(atts, key=lambda a: a["acquired_at"]) if a["competency_id"] == t["competency_id"]
                      and level_ok(a["level"], t["level"]) and a["evidence_type"] in accepted and a["acquired_at"] <= enrolled_at), None)
        if match:
            recognized_comps.append({"competency_id": t["competency_id"], "level": match["level"], "attainment_id": str(match["_id"]),
                                     "module_id": match["module_id"], "evidence_type": match["evidence_type"], "acquired_at": match["acquired_at"]})
    return {"modules": recognized_modules, "competencies": recognized_comps}


async def other_pathway_source(user_id: str, module_id: str, exclude: str) -> str:
    async for e in db.enrollments.find({"user_id": user_id, "pathway_id": {"$ne": exclude}}):
        pv = await pathway_version(e["pathway_id"], e["pathway_version"])
        for pc in pv["pathway_courses"]:
            c = await course_for(pc)
            if c and module_id in c["module_ids"]:
                return e["pathway_id"]
    return None


async def pathway_progress(user: User, pathway_id: str) -> dict:
    enrollment = await db.enrollments.find_one({"user_id": user.id, "pathway_id": pathway_id})
    pv = await pathway_version(pathway_id, enrollment["pathway_version"] if enrollment else None)
    courses = {c["id"]: c for c in await published("courses", "course_versions")}
    cvs = await versions_by_key("course_versions")
    mods = await module_index()
    done, by_module, resources, _ = await user_state(user.id)
    rec = enrollment["recognized"] if enrollment else {"modules": [], "competencies": []}
    rec_mods = {r["module_id"]: r for r in rec["modules"]}
    groups: Dict[str, list] = {"mandatory": [], "optional": []}
    for pc in pv["pathway_courses"]:
        course = pinned(cvs, pc["course_id"], pc.get("course_version")) or courses.get(pc["course_id"])
        if not course:
            continue
        cp = course_progress(course, mods, done, by_module, resources)
        cp["course_version"] = course["version"]
        for m in cp["modules"]:
            r = rec_mods.get(m["module_id"])
            m["recognized"] = bool(r) and m["status"] == "completed"
            if m["recognized"]:
                m["recognition"] = {**r, "source_pathway_id": await other_pathway_source(user.id, m["module_id"], pathway_id)}
        cp["bridge"] = pc["bridge"]
        groups[pc["group"]].append(cp)
    atts = await valid_attainments(user.id)
    rec_comps = {r["competency_id"]: r for r in rec["competencies"]}
    targets = []
    for t in pv["target_competencies"]:
        best = [a for a in atts if a["competency_id"] == t["competency_id"]]
        reached = [a for a in best if level_ok(a["level"], t["level"])]
        top = max(best, key=lambda a: LEVEL_ORDER.index(a["level"]), default=None)
        targets.append({"competency_id": t["competency_id"], "required_level": t["level"], "status": "acquired" if reached else "in_progress" if best else "not_started",
                        "current_level": top["level"] if top else None, "recognized": t["competency_id"] in rec_comps and bool(reached),
                        "recognition": rec_comps.get(t["competency_id"]),
                        "evidence": {"module_id": reached[0]["module_id"], "evidence_type": reached[0]["evidence_type"], "acquired_at": reached[0]["acquired_at"]} if reached else None})
    mandatory = groups["mandatory"]
    return {"pathway_id": pathway_id, "title": pv["title"], "pathway_version": pv["version"],
            "enrolled": bool(enrollment), "enrolled_at": enrollment["enrolled_at"] if enrollment else None,
            "percent": round(sum(c["percent"] for c in mandatory) / len(mandatory), 4) if mandatory else 0,
            "groups": groups, "targets": targets, "recognized_counts": {"modules": len(rec["modules"]), "competencies": len(rec["competencies"])}}


@router.post("/pathways/{pathway_id}/enroll")
async def enroll(pathway_id: str, user: User = Depends(require_learner)):
    existing = await db.enrollments.find_one({"user_id": user.id, "pathway_id": pathway_id})
    if not existing:
        pv = await pathway_version(pathway_id)
        enrolled_at = now_iso()
        await db.enrollments.insert_one({"user_id": user.id, "pathway_id": pathway_id, "pathway_version": pv["version"], "status": "active",
                                         "enrolled_at": enrolled_at, "recognized": await recognition_snapshot(user.id, pv, enrolled_at)})
    return await pathway_progress(user, pathway_id)


@router.get("/learners/me/pathways/{pathway_id}/progress")
async def get_pathway_progress(pathway_id: str, user: User = Depends(require_learner)):
    return await pathway_progress(user, pathway_id)


@router.get("/learners/me/pathways")
async def my_pathways(user: User = Depends(require_learner)):
    out = []
    async for e in db.enrollments.find({"user_id": user.id}).sort("enrolled_at", 1):
        p = await pathway_progress(user, e["pathway_id"])
        out.append({k: p[k] for k in ["pathway_id", "title", "pathway_version", "enrolled_at", "percent", "recognized_counts", "targets"]})
    return out
