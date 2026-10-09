import os
from typing import List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from starlette.middleware.cors import CORSMiddleware

from core import (db, client, logger, BaseDocument, VersionedEntity, EntityVersion, SEED_DATE, LEVEL_ORDER,
                  VERSION_STATUSES, upsert, insert_missing, norm, all_docs, published, versions_by_key, pinned)
import admin
import catalog_io
from seed_catalog import seed_catalog
import auth
import learning
import pathways_api
import projects
import certificates
from seed_assessments import seed_assessments
from seed_phase3 import seed_phase3

from seed_taxonomy import STAGES, PHASES, LAYERS, COMPETENCIES, LEVELS, PROFILES
from seed_concepts import CONCEPTS
from seed_modules import MODULES
from seed_paths import COURSES, PATHWAYS
from seed_demo import SCENARIO, SCENARIO_GENERAL

app = FastAPI(title="CASA AI Academy API", openapi_url="/api/openapi.json", docs_url="/api/docs", redoc_url=None)
api = APIRouter(prefix="/api")


# ---------- Seeding (idempotent upsert) ----------
async def seed_versioned(entity_coll: str, version_coll: str, items: List[dict], transform=None):
    for item in items:
        content = {k: v for k, v in item.items() if k != "_id"}
        if transform:
            content = await transform(item["_id"], content)
        await insert_missing(entity_coll, VersionedEntity(_id=item["_id"], code=item["code"], published_version=1,
                                                  latest_version=1, created_at=SEED_DATE, updated_at=SEED_DATE))
        await insert_missing(version_coll, EntityVersion(_id=f"{item['_id']}@1", entity_id=item["_id"], version=1,
                                                 status="published", changelog="Version initiale",
                                                 created_at=SEED_DATE, published_at=SEED_DATE, **content))


async def module_transform(mid: str, content: dict) -> dict:
    resource_ids = []
    for i, res in enumerate(content.pop("resources"), start=1):
        rid = f"{mid}-R{i}"
        resource_ids.append(rid)
        await insert_missing("resources", BaseDocument(_id=rid, module_id=mid, order=i, version=1, status="published", **res))
    content["resource_ids"] = resource_ids
    return content


async def seed():
    for coll, items in [("stages", STAGES), ("phases", PHASES), ("layers", LAYERS), ("competencies", COMPETENCIES),
                        ("levels", LEVELS), ("profiles", PROFILES)]:
        for item in items:
            await upsert(coll, BaseDocument(**item))
    for item in CONCEPTS:
        await insert_missing("concepts", BaseDocument(**item))
    await upsert("demo_scenarios", BaseDocument(**SCENARIO))
    await upsert("demo_scenarios", BaseDocument(**SCENARIO_GENERAL))
    await seed_versioned("modules", "module_versions", MODULES, module_transform)
    await seed_versioned("courses", "course_versions", COURSES)
    await seed_versioned("pathways", "pathway_versions", PATHWAYS)
    for coll in ["module_versions", "course_versions", "pathway_versions"]:
        await db[coll].create_index([("entity_id", 1), ("version", 1)], unique=True)


@app.on_event("startup")
async def on_startup():
    await seed()
    await seed_assessments()
    await auth.seed_users()
    await learning.create_indexes()
    await seed_phase3()
    await admin.migrate()
    await seed_catalog()
    projects.startup_storage()
    logger.info("Seed data upserted")


@app.on_event("shutdown")
async def on_shutdown():
    client.close()


# ---------- Helpers ----------
def sort_levels(levels) -> List[str]:
    return sorted(set(levels), key=LEVEL_ORDER.index)


def count_words(*texts) -> int:
    return sum(len(str(t or "").split()) for t in texts)


async def module_minutes(mod: dict) -> int:
    res = await db.resources.find({"_id": {"$in": mod.get("resource_ids", [])}}).to_list(100)
    words = sum(count_words(sec.get("heading"), sec.get("body")) for r in res for sec in r.get("sections") or [])
    questions = 0
    for suffix in ("F", "G"):
        a = await db.assessments.find_one({"_id": f"A-{mod['id']}-{suffix}"})
        if a and a.get("published_version"):
            v = await db.assessment_versions.find_one({"entity_id": a["_id"], "version": a["published_version"]})
            questions += len((v or {}).get("questions", []))
    return max(1, round(words / 200 + questions))


def module_summary(mod: dict) -> dict:
    keys = ["id", "code", "title", "summary", "levels", "layer_ids", "stage_ids", "competency_ids", "duration_hours", "version", "status"]
    s = {k: mod.get(k) for k in keys}
    s["resource_count"] = len(mod.get("resource_ids", []))
    return s


def enrich_concepts(concepts: List[dict], modules: List[dict]) -> List[dict]:
    by_id = {m["id"]: m for m in modules}
    for c in concepts:
        linked = [by_id[mid] for mid in c["module_ids"] if mid in by_id]
        c["levels"] = sort_levels(lv for m in linked for lv in m["levels"])
        c["competency_ids"] = sorted({cid for m in linked for cid in m["competency_ids"]})
    return concepts


async def load_modules() -> List[dict]:
    return await published("modules", "module_versions")


async def load_concepts(modules: List[dict]) -> List[dict]:
    return enrich_concepts(await all_docs("concepts", "_id"), modules)


def matches(item: dict, stage, layer, level, competency, q, text_fields) -> bool:
    if stage and stage not in item["stage_ids"]:
        return False
    if layer and layer not in item["layer_ids"]:
        return False
    if level and level not in item["levels"]:
        return False
    if competency and competency not in item["competency_ids"]:
        return False
    if q and norm(q) not in norm(" ".join(str(item.get(f, "")) for f in text_fields)):
        return False
    return True


def pick(items: List[dict], ids: List[str], fields: List[str]) -> List[dict]:
    by_id = {i["id"]: i for i in items}
    return [{f: by_id[i].get(f) for f in fields} for i in ids if i in by_id]


# ---------- Catalog ----------
@api.get("/")
async def root():
    return {"name": "CASA AI Academy API", "phase": 1}


@api.get("/catalog/stages")
async def get_stages():
    return await all_docs("stages")


@api.get("/catalog/phases")
async def get_phases():
    return await all_docs("phases")


@api.get("/catalog/competencies")
async def get_competencies():
    return await all_docs("competencies")


@api.get("/catalog/levels")
async def get_levels():
    return await all_docs("levels")


@api.get("/catalog/profiles")
async def get_profiles():
    return await all_docs("profiles")


async def layers_with_links() -> List[dict]:
    layers = await all_docs("layers")
    modules = await load_modules()
    concepts = await all_docs("concepts", "_id")
    for layer in layers:
        layer["modules"] = [{"id": m["id"], "code": m["code"], "title": m["title"], "levels": m["levels"]}
                            for m in modules if layer["id"] in m["layer_ids"]]
        layer["concept_ids"] = [c["id"] for c in concepts if layer["id"] in c["layer_ids"]]
    return layers


@api.get("/catalog/layers")
async def get_layers():
    return await layers_with_links()


@api.get("/catalog/layers/{layer_id}")
async def get_layer(layer_id: str):
    for layer in await layers_with_links():
        if layer["id"] == layer_id:
            return layer
    raise HTTPException(404, "Couche introuvable")


@api.get("/catalog/overview")
async def get_overview():
    return {
        "stages": await all_docs("stages"), "phases": await all_docs("phases"), "layers": await layers_with_links(),
        "competencies": await all_docs("competencies"), "levels": await all_docs("levels"),
        "profiles": await all_docs("profiles"), "version_statuses": VERSION_STATUSES,
    }


# ---------- Demo ----------
@api.get("/demo/scenarios")
async def list_scenarios():
    docs = await db.demo_scenarios.find({}, {"steps": 0, "quiz": 0}).sort("order", 1).to_list(100)
    return [BaseDocument.from_mongo(d).out() for d in docs]


@api.get("/demo/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str):
    doc = BaseDocument.from_mongo(await db.demo_scenarios.find_one({"_id": scenario_id}))
    if not doc:
        raise HTTPException(404, "Scénario introuvable")
    return doc.out()


# ---------- Concepts ----------
@api.get("/concepts")
async def list_concepts(stage: Optional[str] = None, layer: Optional[str] = None, level: Optional[str] = None,
                        competency: Optional[str] = None, q: Optional[str] = Query(None, max_length=120)):
    concepts = await load_concepts(await load_modules())
    return [c for c in concepts if matches(c, stage, layer, level, competency, q, ["name", "short", "definition"])]


@api.get("/concepts/{concept_id}")
async def get_concept(concept_id: str):
    modules = await load_modules()
    concepts = await load_concepts(modules)
    concept = next((c for c in concepts if c["id"] == concept_id), None)
    if not concept:
        raise HTTPException(404, "Notion introuvable")
    stages, layers = await all_docs("stages"), await all_docs("layers")
    concept["stages"] = pick(stages, concept["stage_ids"], ["id", "code", "name", "subtitle"])
    concept["layers"] = pick(layers, concept["layer_ids"], ["id", "name", "color", "short"])
    concept["prerequisites"] = pick(concepts, concept["prerequisite_ids"], ["id", "name", "short"])
    concept["modules"] = pick(modules, concept["module_ids"], ["id", "code", "title", "levels", "summary"])
    concept["dependents"] = [{"id": c["id"], "name": c["name"]} for c in concepts if concept_id in c["prerequisite_ids"]]
    concept["estimated_minutes"] = max(1, round(count_words(concept["definition"], concept["example"], *(concept.get("treatment") or {}).values()) / 200))
    concept["competencies"] = pick(await all_docs("competencies"), concept["competency_ids"], ["id", "name", "category_id"])
    return concept


# ---------- Modules ----------
@api.get("/modules")
async def list_modules(stage: Optional[str] = None, layer: Optional[str] = None, level: Optional[str] = None,
                       competency: Optional[str] = None, q: Optional[str] = Query(None, max_length=120)):
    modules = await load_modules()
    return [module_summary(m) for m in modules
            if matches(m, stage, layer, level, competency, q, ["code", "title", "summary", "objectives"])]


@api.get("/modules/{module_id}")
async def get_module(module_id: str):
    modules = await load_modules()
    mod = next((m for m in modules if m["id"] == module_id), None)
    if not mod:
        raise HTTPException(404, "Module introuvable")
    res_docs = await db.resources.find({"_id": {"$in": mod["resource_ids"]}}).sort("order", 1).to_list(100)
    mod["resources"] = [BaseDocument.from_mongo(d).out() for d in res_docs]
    stages, layers, comps = await all_docs("stages"), await all_docs("layers"), await all_docs("competencies")
    mod["stages"] = pick(stages, mod["stage_ids"], ["id", "code", "name"])
    mod["layers"] = pick(layers, mod["layer_ids"], ["id", "name", "color", "short"])
    mod["competencies"] = pick(comps, mod["competency_ids"], ["id", "name", "description", "category_id"])
    mod["prerequisite_modules"] = pick(modules, mod["prerequisite_module_ids"], ["id", "code", "title"])
    mod["estimated_minutes"] = await module_minutes(mod)
    concepts = await all_docs("concepts", "_id")
    mod["concepts"] = [{"id": c["id"], "name": c["name"], "short": c["short"]} for c in concepts if module_id in c["module_ids"]]
    courses = await published("courses", "course_versions")
    mod["courses"] = [{"id": c["id"], "code": c["code"], "title": c["title"], "pinned_version": (c.get("module_pins") or {}).get(module_id)}
                      for c in courses if module_id in c["module_ids"]]
    return mod


@api.get("/modules/{module_id}/versions")
async def get_module_versions(module_id: str):
    docs = await db.module_versions.find({"entity_id": module_id}, {"version": 1, "status": 1, "changelog": 1,
                                                                     "created_at": 1, "published_at": 1}).sort("version", 1).to_list(100)
    if not docs:
        raise HTTPException(404, "Module introuvable")
    return [BaseDocument.from_mongo(d).out() for d in docs]


@api.get("/resources/{resource_id}/file")
async def get_resource_file(resource_id: str):
    doc = await db.resources.find_one({"_id": resource_id})
    if not doc or not doc.get("file"):
        raise HTTPException(404, "Aucun fichier pour cette ressource")
    data = await run_in_threadpool(projects.get_object, doc["file"]["storage_path"])
    return Response(content=data, media_type=doc["file"]["content_type"],
                    headers={"Content-Disposition": f'attachment; filename="{doc["file"]["original_filename"]}"'})


@api.get("/resources/{resource_id}")
async def get_resource(resource_id: str):
    doc = BaseDocument.from_mongo(await db.resources.find_one({"_id": resource_id}))
    if not doc:
        raise HTTPException(404, "Ressource introuvable")
    return doc.out()


# ---------- Courses & pathways ----------
async def course_detail(course: dict, modules: List[dict]) -> dict:
    by_id = {m["id"]: m for m in modules}
    versions = await versions_by_key("module_versions")
    pins, optional = course.get("module_pins") or {}, set(course.get("optional_module_ids") or [])
    course["modules"] = []
    for mid in course["module_ids"]:
        mod = pinned(versions, mid, pins.get(mid)) or by_id.get(mid)
        if mod:
            course["modules"].append({**module_summary(mod), "pinned_version": mod["version"], "optional": mid in optional, "estimated_minutes": await module_minutes(mod)})
    course["estimated_minutes"] = sum(m["estimated_minutes"] for m in course["modules"])
    return course


@api.get("/courses")
async def list_courses():
    modules = await load_modules()
    return [await course_detail(c, modules) for c in await published("courses", "course_versions")]


@api.get("/courses/{course_id}")
async def get_course(course_id: str):
    courses = await published("courses", "course_versions")
    course = next((c for c in courses if c["id"] == course_id), None)
    if not course:
        raise HTTPException(404, "Cours introuvable")
    pathways = await published("pathways", "pathway_versions")
    course["pathways"] = [{"id": p["id"], "title": p["title"]} for p in pathways if course_id in p["course_ids"]]
    return await course_detail(course, await load_modules())


async def pathway_detail(pathway: dict, courses: List[dict], modules: List[dict]) -> dict:
    by_id = {c["id"]: c for c in courses}
    versions = await versions_by_key("course_versions")
    pins = {pc["course_id"]: pc.get("course_version") for pc in pathway.get("pathway_courses", [])}
    pathway["courses"] = []
    for cid in pathway["course_ids"]:
        course = pinned(versions, cid, pins.get(cid)) or by_id.get(cid)
        if course:
            pathway["courses"].append(await course_detail(dict(course), modules))
    return pathway


@api.get("/pathways")
async def list_pathways():
    modules, courses = await load_modules(), await published("courses", "course_versions")
    return [await pathway_detail(p, courses, modules) for p in await published("pathways", "pathway_versions")]


@api.get("/pathways/{pathway_id}")
async def get_pathway(pathway_id: str):
    pathways = await published("pathways", "pathway_versions")
    pathway = next((p for p in pathways if p["id"] == pathway_id), None)
    if not pathway:
        raise HTTPException(404, "Parcours introuvable")
    return await pathway_detail(pathway, await published("courses", "course_versions"), await load_modules())


app.include_router(api)
app.include_router(auth.router)
app.include_router(learning.router)
app.include_router(pathways_api.router)
app.include_router(projects.router)
app.include_router(certificates.router)
app.include_router(admin.router)
app.include_router(catalog_io.router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
