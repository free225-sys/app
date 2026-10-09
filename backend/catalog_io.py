import re
from datetime import date
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import User, require_roles
from core import LEVEL_ORDER, db, log_change, norm, now_iso
from admin import BRIDGE, PUBLISHERS, TYPES, content_of, normalize, validate_shape, write_draft

router = APIRouter(prefix="/api", tags=["catalog"])

LAYER_CODES = {"layer-application": "APPLICATION", "layer-donnees": "DONNEES", "layer-mathematiques": "MATHEMATIQUES", "layer-modeles": "MODELES",
               "layer-infrastructure": "INFRASTRUCTURE", "layer-securite": "SECURITE_GOUVERNANCE"}
CODE_LAYERS = {v: k for k, v in LAYER_CODES.items()}
ASSET_TYPES = {"Texte": "text", "Schéma commenté": "diagram", "Étude de cas": "case", "Exercice interactif": "interactive", "Vidéo": "video",
               "Fiche synthèse": "sheet", "Exercice guidé": "exercise", "Fichier": "file"}
TYPE_ASSETS = {v: k for k, v in ASSET_TYPES.items()}
REUSE_RULE = ("Une ressource est versionnee et peut etre rattachee a plusieurs modules. Un module peut etre partage par plusieurs cours. "
              "Une competence validee est reconnue dans tout parcours compatible.")
TODO = "À compléter dans le back-office."


def stage_code(sid):
    return f"ST{sid[-2:]}" if sid else None


def strip_v(ref: str):
    m = re.match(r"^(.+?):v(\d+)$", ref)
    return (m.group(1), int(m.group(2))) if m else (ref, None)


async def published_docs(t: str) -> List[dict]:
    cfg = TYPES[t]
    out = []
    async for e in db[cfg["entity"]].find({"published_version": {"$nin": [None]}}).sort("_id", 1):
        v = await db[cfg["versions"]].find_one({"entity_id": e["_id"], "version": e["published_version"]})
        if v:
            out.append({**content_of(v), "_id": e["_id"], "version": v["version"], "catalog_id": e.get("catalog_id") or v.get("catalog_id")})
    return out


def ext(doc: dict) -> str:
    return doc.get("catalog_id") or doc["_id"]


def credential_conditions(rules: List[dict], aext: Dict[str, str]) -> dict:
    return {"competency_evidence": [{"id": r["competency_id"], "min_level": r["min_level"]} for r in rules if r.get("kind") != "assessment_passed"],
            "graded_assessments_passed": [aext.get(r["assessment_id"], r["assessment_id"]) for r in rules if r.get("kind") == "assessment_passed"]}


@router.get("/admin/catalog/export")
async def export_catalog(user: User = Depends(require_roles(*PUBLISHERS))):
    concepts, modules, resources = await published_docs("concept"), await published_docs("module"), await published_docs("resource")
    assessments, courses, pathways = await published_docs("assessment"), await published_docs("course"), await published_docs("pathway")
    credentials = await published_docs("credential")
    rubrics = [r async for r in db.rubrics.find({"status": "published"})]
    cext = {c["_id"]: ext(c) for c in concepts}
    aext = {a["_id"]: ext(a) for a in assessments} | {r["rubric_id"]: r.get("catalog_id") or r["rubric_id"] for r in rubrics}
    comps = await db.competencies.find().sort("order", 1).to_list(100)
    qcomps = {}
    for a in assessments:
        ids = {f"{q['question_id']}@{q['version']}" for q in a["questions"]}
        qcomps[a["_id"]] = sorted({c["competency_id"] async for q in db.questions.find({"_id": {"$in": list(ids)}}) for c in q["competencies"]})
    out_assess = [{"id": aext[a["_id"]], "type": a.get("catalog_type") or {"graded": "graded_quiz", "formative": "practice_quiz"}.get(a["kind"], a["kind"]),
                   "module": a.get("module_id"), "competencies": qcomps[a["_id"]],
                   **({"passing_score": round(a["pass_threshold"] * 100)} if a["kind"] == "graded" and a.get("pass_threshold") else {})} for a in assessments]
    out_assess += [{"id": aext[r["rubric_id"]], "type": "project", "module": r["module_id"], "competencies": r["competency_ids"], "passing_score": round(r["pass_threshold"] * 100)} for r in rubrics]
    return {
        "catalogue_version": f"casa-{date.today().isoformat()}", "status": "publie", "exported_at": now_iso(),
        "stages": [{"id": stage_code(s["_id"]), "name": s["name"]} async for s in db.stages.find().sort("order", 1)],
        "layers": [LAYER_CODES[lid["_id"]] async for lid in db.layers.find().sort("order", 1)],
        "concepts": [{"id": cext[c["_id"]], "name": c["name"], "primary_stage": stage_code(c.get("primary_stage") or (c["stage_ids"] or [None])[0]),
                      "layers": [LAYER_CODES[x] for x in c["layer_ids"]], "prerequisites": [cext.get(p, p) for p in c["prerequisite_ids"]]} for c in concepts],
        "competencies": [{"id": k["_id"], "description": k.get("description") or k["name"], "levels": k.get("levels", LEVEL_ORDER)} for k in comps],
        "modules": [{"id": m["_id"], "title": m["title"], "level": m["levels"][0] if m["levels"] else "L0", "levels": m["levels"],
                     "concepts": [cext[c["_id"]] for c in concepts if m["_id"] in c["module_ids"]], "competencies": m["competency_ids"],
                     "prerequisites": m["prerequisite_module_ids"], "assets": [f"{r}:v{next((x['version'] for x in resources if x['_id'] == r), 1)}" for r in m["resource_ids"]],
                     "assessments": [aext[a["_id"]] for a in assessments if a.get("module_id") == m["_id"]] + [aext[r["rubric_id"]] for r in rubrics if r["module_id"] == m["_id"]]}
                    for m in modules],
        "learning_assets": [{"id": r["_id"], "version": r["version"], "type": ASSET_TYPES.get(r["type"], r["type"]), "title": r["title"]} for r in resources],
        "courses": [{"id": c["_id"], "version": c["version"], "title": c["title"],
                     "modules": [{"module_id": mid, "required": mid not in c.get("optional_module_ids", [])} for mid in c["module_ids"]]} for c in courses],
        "pathways": [{"id": p["_id"], "version": p["version"], "title": p["title"],
                      "courses": [f"{pc['course_id']}:v{pc.get('course_version') or 1}" for pc in p["pathway_courses"]]} for p in pathways],
        "assessments": out_assess,
        "credential_examples": [{"id": c["_id"], "title": c["title"], "conditions": credential_conditions(c["rules"], aext)} for c in credentials],
        "reuse_rule": REUSE_RULE,
    }


# ---------- Import ----------
class Plan:
    def __init__(self):
        self.items, self.errors, self.warnings, self.new_comps = [], [], [], []

    def err(self, msg):
        self.errors.append(msg)


async def latest(t: str, eid: str):
    return await db[TYPES[t]["versions"]].find_one({"entity_id": eid}, sort=[("version", -1)])


async def find_cycle(graph: Dict[str, List[str]]):
    state = {}

    def visit(n, path):
        if state.get(n) == 1:
            return path[path.index(n):] + [n]
        if state.get(n) == 2:
            return None
        state[n] = 1
        for p in graph.get(n, []):
            c = visit(p, path + [n])
            if c:
                return c
        state[n] = 2
        return None
    for node in list(graph):
        c = visit(node, [])
        if c:
            return c
    return None


async def build_plan(data: Dict[str, Any]) -> Plan:
    plan = Plan()
    if not isinstance(data, dict) or "catalogue_version" not in data:
        raise HTTPException(400, "Fichier invalide : champ catalogue_version manquant.")
    lists = {k: data.get(k) or [] for k in ["stages", "layers", "concepts", "competencies", "modules", "learning_assets", "courses", "pathways", "assessments", "credential_examples"]}
    stages = {s["_id"] async for s in db.stages.find({}, {"_id": 1})}
    comp_ids = {c["_id"] async for c in db.competencies.find({}, {"_id": 1})}
    for k in lists["competencies"]:
        if k.get("id") not in comp_ids:
            plan.new_comps.append(k)
    comp_ids |= {k.get("id") for k in lists["competencies"]}

    def stage(code):
        sid = f"stage-{code[2:]}" if code and code.startswith("ST") else code
        if sid not in stages:
            plan.err(f"Étape inconnue : {code}.")
        return sid

    def layer(code):
        lid = CODE_LAYERS.get(code, code)
        if lid not in LAYER_CODES:
            plan.err(f"Couche inconnue : {code}.")
        return lid

    concept_docs = await db.concepts.find().to_list(1000)
    cmap = {}
    for c in concept_docs:
        cmap[c["_id"]] = cmap[norm(c["name"])] = c["_id"]
        if c.get("catalog_id"):
            cmap[c["catalog_id"]] = c["_id"]
    for c in lists["concepts"]:
        cmap.setdefault(c["id"], cmap.get(norm(c.get("name", ""))) or c["id"])
    assessments = await db.assessments.find().to_list(1000)
    amap = {a["_id"]: a["_id"] for a in assessments} | {a["catalog_id"]: a["_id"] for a in assessments if a.get("catalog_id")}
    async for r in db.rubrics.find({"status": "published"}):
        amap[r["rubric_id"]] = amap[r.get("catalog_id") or r["rubric_id"]] = r["rubric_id"]
    file_mods = {m["id"]: m for m in lists["modules"]}
    for a in lists["assessments"]:
        if a["id"] not in amap:
            owner = next((m["id"] for m in lists["modules"] if a["id"] in m.get("assessments", [])), None) or a.get("module")
            amap[a["id"]] = f"A-{owner}-{'G' if a.get('type') == 'graded_quiz' else 'F'}" if owner and a.get("type") != "project" else None
    known = {t: {d["entity_id"] async for d in db[TYPES[t]["versions"]].find({}, {"entity_id": 1})} for t in ("module", "resource", "course", "pathway")}
    file_ids = {"module": set(file_mods), "resource": {a["id"] for a in lists["learning_assets"]}, "course": {c["id"] for c in lists["courses"]},
                "pathway": {p["id"] for p in lists["pathways"]}}

    def ref(t, rid, where):
        if rid not in known[t] and rid not in file_ids[t]:
            plan.err(f"{where} : référence inconnue « {rid} ».")
        return rid

    async def add(t, eid, src, merged: dict, title):
        cur = await latest(t, eid)
        try:
            content = await normalize(t, validate_shape(t, merged))
        except HTTPException as e:
            plan.err(f"{TYPES[t]['label']} {src} : {e.detail}")
            return
        base = content_of(cur) if cur else {}
        changes = sorted(k for k in set(base) | set(content) if base.get(k) != content.get(k))
        action = "create" if not cur else ("unchanged" if not changes else "update")
        if action == "update" and cur["status"] == "review":
            plan.err(f"{TYPES[t]['label']} {eid} : une version est en relecture, import impossible.")
        plan.items.append({"type": t, "label": TYPES[t]["label"], "id": eid, "source_id": src, "title": title, "action": action,
                           "changes": changes if cur else [], "content": content})

    concept_links: Dict[str, set] = {}
    for m in lists["modules"]:
        for c in m.get("concepts", []):
            if c not in cmap:
                plan.err(f"Module {m['id']} : notion inconnue « {c} ».")
            else:
                concept_links.setdefault(cmap[c], set()).add(m["id"])
    cgraph = {c["_id"]: c.get("prerequisite_ids", []) for c in concept_docs}
    for c in lists["concepts"]:
        eid = cmap[c["id"]]
        cur = await latest("concept", eid)
        base = content_of(cur) if cur else {"short": TODO, "definition": TODO, "example": TODO, "treatment": {}, "stage_ids": [], "module_ids": []}
        prereqs = []
        for p in c.get("prerequisites", []):
            if p not in cmap:
                plan.err(f"Notion {c['id']} : prérequis inconnu « {p} ».")
            else:
                prereqs.append(cmap[p])
        ps = stage(c.get("primary_stage"))
        merged = {**base, "name": c.get("name", ""), "primary_stage": ps, "layer_ids": [layer(x) for x in c.get("layers", [])], "prerequisite_ids": prereqs,
                  "stage_ids": base["stage_ids"] if ps in base["stage_ids"] else [ps] + base["stage_ids"],
                  "module_ids": sorted(set(base["module_ids"]) | concept_links.get(eid, set())) if concept_links.get(eid, set()) - set(base["module_ids"]) else base["module_ids"]}
        if c["id"] != eid or base.get("catalog_id"):
            merged["catalog_id"] = base.get("catalog_id") or (c["id"] if c["id"] != eid else None)
        cgraph[eid] = prereqs
        await add("concept", eid, c["id"], merged, c.get("name"))
    cycle = await find_cycle(cgraph)
    if cycle:
        plan.err(f"Cycle de prérequis entre notions : {' → '.join(cycle)}.")
    for a in lists["learning_assets"]:
        cur = await latest("resource", a["id"])
        owner = next((m["id"] for m in lists["modules"] if a["id"] in [strip_v(x)[0] for x in m.get("assets", [])]), None)
        base = content_of(cur) if cur else {"module_id": owner, "order": 1, "duration_min": 10, "sections": [{"heading": a.get("title", ""), "body": TODO}]}
        await add("resource", a["id"], a["id"], {**base, "title": a.get("title", ""), "type": TYPE_ASSETS.get(a.get("type"), a.get("type") or "Texte")}, a.get("title"))
    mgraph = {}
    async for e in db.modules.find({"published_version": {"$nin": [None]}}):
        v = await db.module_versions.find_one({"entity_id": e["_id"], "version": e["published_version"]})
        mgraph[e["_id"]] = (v or {}).get("prerequisite_module_ids", [])
    for m in lists["modules"]:
        cur = await latest("module", m["id"])
        linked = [cmap[c] for c in m.get("concepts", []) if c in cmap]
        cdocs = [d for d in concept_docs if d["_id"] in linked]
        base = content_of(cur) if cur else {"code": m["id"], "summary": TODO, "objectives": [], "prerequisites": [], "duration_hours": 1,
                                            "layer_ids": sorted({x for d in cdocs for x in d["layer_ids"]}), "stage_ids": sorted({d.get("primary_stage") or d["stage_ids"][0] for d in cdocs})}
        levels = m.get("levels") or (base.get("levels") if m.get("level") in (base.get("levels") or []) else [m.get("level", "L0")])
        for k in m.get("competencies", []):
            if k not in comp_ids:
                plan.err(f"Module {m['id']} : compétence inconnue « {k} ».")
        for q in m.get("assessments", []):
            if q not in amap and q not in {x["id"] for x in lists["assessments"]}:
                plan.err(f"Module {m['id']} : évaluation inconnue « {q} ».")
        prereqs = [ref("module", p, f"Module {m['id']}") for p in m.get("prerequisites", [])]
        mgraph[m["id"]] = prereqs
        await add("module", m["id"], m["id"], {**base, "title": m.get("title", ""), "levels": levels, "competency_ids": m.get("competencies", []), "prerequisite_module_ids": prereqs,
                                                "resource_ids": [ref("resource", strip_v(x)[0], f"Module {m['id']}") for x in m.get("assets", [])]}, m.get("title"))
    cycle = await find_cycle(mgraph)
    if cycle:
        plan.err(f"Cycle de prérequis entre modules : {' → '.join(cycle)}.")
    for a in lists["assessments"]:
        aid = amap.get(a["id"])
        for k in a.get("competencies", []):
            if k not in comp_ids:
                plan.err(f"Évaluation {a['id']} : compétence inconnue « {k} ».")
        if a.get("type") == "project" or not aid:
            if not aid:
                plan.warnings.append(f"Évaluation {a['id']} : les projets se configurent par une grille dans le back-office ; non importé.")
            continue
        cur = await latest("assessment", aid)
        graded = a.get("type") == "graded_quiz"
        base = content_of(cur) if cur else {"code": aid, "kind": "graded" if graded else "formative", "module_id": aid[2:-2], "title": f"Quiz {a['id']}", "questions": [],
                                            "max_attempts": 3 if graded else None, "pass_threshold": 0.7 if graded else None, "catalog_id": a["id"], "catalog_type": a.get("type")}
        merged = {**base, **({"pass_threshold": a["passing_score"] / 100} if a.get("passing_score") is not None and graded else {})}
        await add("assessment", aid, a["id"], merged, base.get("title"))
    for c in lists["courses"]:
        cur = await latest("course", c["id"])
        mods = [ref("module", x["module_id"], f"Cours {c['id']}") for x in c.get("modules", [])]
        base = content_of(cur) if cur else {"code": c["id"], "summary": TODO, "profile_id": "", "levels": [], "module_pins": {}, "duration_hours": 1}
        await add("course", c["id"], c["id"], {**base, "title": c.get("title", ""), "module_ids": mods, "module_pins": {m: base["module_pins"].get(m) for m in mods},
                                                "optional_module_ids": [x["module_id"] for x in c.get("modules", []) if x.get("required") is False]}, c.get("title"))
    for p in lists["pathways"]:
        cur = await latest("pathway", p["id"])
        base = content_of(cur) if cur else {"code": p["id"], "summary": TODO, "profile_ids": [], "levels": [], "target_competencies": [], "pathway_courses": []}
        old = {pc["course_id"]: pc for pc in base["pathway_courses"]}
        pcs = []
        for r in p.get("courses", []):
            cid, ver = strip_v(r)
            ref("course", cid, f"Parcours {p['id']}")
            pcs.append({**old.get(cid, {"group": "mandatory", "bridge": BRIDGE}), "course_id": cid, "course_version": ver or old.get(cid, {}).get("course_version")})
        await add("pathway", p["id"], p["id"], {**base, "title": p.get("title", ""), "pathway_courses": pcs}, p.get("title"))
    for cr in lists["credential_examples"]:
        cur = await latest("credential", cr["id"])
        base = content_of(cur) if cur else {"code": cr["id"], "summary": TODO, "rules": []}
        cond = cr.get("conditions") or {}
        aext = {v: k for k, v in amap.items() if v and k != v}
        if credential_conditions(base["rules"], aext) != {"competency_evidence": cond.get("competency_evidence", []), "graded_assessments_passed": cond.get("graded_assessments_passed", [])}:
            rules = []
            for i, ce in enumerate(cond.get("competency_evidence", []), 1):
                if ce.get("id") not in comp_ids:
                    plan.err(f"Certification {cr['id']} : compétence inconnue « {ce.get('id')} ».")
                rules.append({"id": f"r{i}", "label": f"{ce.get('id')} (niveau {ce.get('min_level')})", "competency_id": ce.get("id"), "min_level": ce.get("min_level", "L0"),
                              "module_id": None, "evidence_types": ["graded_attempt", "project"], "min_score": 0})
            for q in cond.get("graded_assessments_passed", []):
                if not amap.get(q):
                    plan.err(f"Certification {cr['id']} : évaluation inconnue « {q} ».")
                rules.append({"id": f"r{len(rules) + 1}", "kind": "assessment_passed", "label": f"Évaluation notée {q} réussie", "assessment_id": amap.get(q), "competency_id": None, "module_id": None})
            base = {**base, "rules": rules}
        await add("credential", cr["id"], cr["id"], {**base, "title": cr.get("title", "")}, cr.get("title"))
    return plan


def plan_out(plan: Plan) -> dict:
    counts = {a: sum(i["action"] == a for i in plan.items) for a in ("create", "update", "unchanged")}
    return {"summary": {**counts, "new_competencies": len(plan.new_comps), "errors": len(plan.errors), "warnings": len(plan.warnings)},
            "items": [{k: v for k, v in i.items() if k != "content"} for i in plan.items], "errors": plan.errors, "warnings": plan.warnings,
            "new_competencies": [k.get("id") for k in plan.new_comps]}


@router.post("/admin/catalog/import")
async def import_catalog(data: Dict[str, Any], confirm: bool = Query(False), user: User = Depends(require_roles(*PUBLISHERS))):
    plan = await build_plan(data)
    out = plan_out(plan)
    if not confirm:
        return out
    if plan.errors:
        raise HTTPException(422, "Import refusé : " + " ".join(plan.errors[:10]))
    for k in plan.new_comps:
        await db.competencies.update_one({"_id": k["id"]}, {"$setOnInsert": {"name": k.get("description", k["id"]), "description": k.get("description", ""), "levels": k.get("levels", []),
                                                                           "kind": "referential", "order": 50}}, upsert=True)
    for i in plan.items:
        if i["action"] != "unchanged":
            await write_draft(i["type"], i["id"], i["content"], f"Import catalogue {data.get('catalogue_version')}", user)
    await log_change(user, "catalog", str(data.get("catalogue_version")), "import",
                     f"{out['summary']['create']} création(s), {out['summary']['update']} mise(s) à jour en brouillon, {out['summary']['unchanged']} inchangé(s)")
    return {**out, "imported": True}
