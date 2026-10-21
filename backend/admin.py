import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Request, APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import ValidationError, BaseModel, EmailStr, Field
from starlette.concurrency import run_in_threadpool

from auth import ROLES, User, get_optional_user, hash_password, require_roles
from core import BaseDocument, db, log_change, norm, now_iso
import projects

router = APIRouter(prefix="/api", tags=["admin"])

STAFF = ("admin",)
AUTHORS = ("admin",)
ASSESSORS = ("admin",)
REVIEWERS = ("admin",)
PUBLISHERS = ("admin",)
S, L, D, N = str, list, dict, (int, float)
BRIDGE = {"module_recognition": "same_module_version", "accepted_evidence_types": ["graded_attempt", "project"]}

TYPES = {
    "concept": {"label": "Notion", "entity": "concepts", "versions": "concept_versions", "projection": True, "title": "name", "editors": AUTHORS, "prefix": "concept-",
                "fields": {"name": S, "short": S, "definition": S, "example": S, "treatment": D, "stage_ids": L, "layer_ids": L, "prerequisite_ids": L, "module_ids": L}},
    "resource": {"label": "Ressource", "entity": "resources", "versions": "resource_versions", "projection": True, "title": "title", "editors": AUTHORS, "prefix": "R-",
                 "fields": {"module_id": S, "title": S, "type": S, "order": N, "duration_min": N, "sections": L}},
    "module": {"label": "Module", "entity": "modules", "versions": "module_versions", "title": "title", "editors": AUTHORS, "prefix": "M-", "entity_fields": ["code"],
               "fields": {"code": S, "title": S, "summary": S, "objectives": L, "prerequisites": L, "prerequisite_module_ids": L, "layer_ids": L,
                          "stage_ids": L, "levels": L, "competency_ids": L, "duration_hours": N, "resource_ids": L}},
    "question": {"label": "Question", "entity": "question_bank", "versions": "questions", "title": "prompt", "editors": ASSESSORS, "prefix": "Q-", "entity_fields": ["module_id"],
                 "fields": {"type": S, "prompt": S, "options": L, "correct": L, "explanation": S, "competencies": L}},
    "assessment": {"label": "Évaluation", "entity": "assessments", "versions": "assessment_versions", "title": "title", "editors": ASSESSORS, "prefix": "A-",
                   "entity_fields": ["code", "kind", "module_id", "title", "pass_threshold", "max_attempts"],
                   "fields": {"code": S, "kind": S, "title": S, "questions": L}},
    "course": {"label": "Cours", "entity": "courses", "versions": "course_versions", "title": "title", "editors": AUTHORS, "prefix": "C-", "entity_fields": ["code"],
               "fields": {"code": S, "title": S, "summary": S, "levels": L, "module_ids": L, "module_pins": D, "optional_module_ids": L, "duration_hours": N}},
    "pathway": {"label": "Parcours", "entity": "pathways", "versions": "pathway_versions", "title": "title", "editors": AUTHORS, "prefix": "P-", "entity_fields": ["code"],
                "fields": {"code": S, "title": S, "summary": S, "profile_ids": L, "levels": L, "pathway_courses": L, "target_competencies": L}},
    "credential": {"label": "Certification", "entity": "credentials", "versions": "credential_versions", "projection": True, "title": "title", "editors": AUTHORS,
                   "prefix": "CERT-", "fields": {"code": S, "title": S, "summary": S, "rules": L}},
}
META = {"_id", "id", "entity_id", "question_id", "version", "status", "approved", "changelog", "created_at", "created_by", "updated_at", "submitted_at", "submitted_by",
        "reviews", "published_at", "published_by", "retired_at", "retired_by", "retire_reason", "superseded", "published_version", "latest_version"}


# ---------- Helpers ----------
def cfg_of(t: str) -> dict:
    if t not in TYPES:
        raise HTTPException(404, "Type de contenu inconnu")
    return TYPES[t]


def who(user: User) -> dict:
    return {"id": user.id, "name": f"{user.first_name} {user.last_name}", "email": user.email}


def has(user: User, roles) -> bool:
    return user.role in roles


def ensure(user: User, roles, message="Action non autorisée pour votre rôle."):
    if not has(user, roles):
        raise HTTPException(403, message)


def content_of(doc: Optional[dict]) -> dict:
    return {k: v for k, v in (doc or {}).items() if k not in META}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", norm(text)).strip("-")[:40] or uuid.uuid4().hex[:6]


def short(v) -> Optional[str]:
    if v is None:
        return None
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s[:300] + "…" if len(s) > 300 else s


def diff(prev: Optional[dict], cur: dict) -> List[dict]:
    a, b = content_of(prev), content_of(cur)
    return [{"field": k, "before": short(a.get(k)), "after": short(b.get(k))} for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]


def meta_out(doc: dict, cfg: dict) -> dict:
    keys = ["version", "status", "approved", "changelog", "created_at", "created_by", "updated_at", "submitted_at", "submitted_by", "reviews",
            "published_at", "published_by", "retired_at", "retired_by", "retire_reason", "superseded"]
    return {**{k: doc.get(k) for k in keys}, "entity_id": doc["entity_id"], "title": short(doc.get(cfg["title"]))}


async def versions_of(t: str, eid: str) -> List[dict]:
    return await db[TYPES[t]["versions"]].find({"entity_id": eid}).sort("version", 1).to_list(500)


async def latest_of(t: str, eid: str) -> dict:
    docs = await versions_of(t, eid)
    if not docs:
        raise HTTPException(404, "Contenu introuvable")
    return docs[-1]


async def entity_doc(t: str, eid: str) -> Optional[dict]:
    return await db[TYPES[t]["entity"]].find_one({"_id": eid})


async def detail(t: str, eid: str) -> dict:
    cfg, docs = TYPES[t], await versions_of(t, eid)
    if not docs:
        raise HTTPException(404, "Contenu introuvable")
    ent = await entity_doc(t, eid)
    history = [{**meta_out(d, cfg), "changes": diff(docs[i - 1] if i else None, d)} for i, d in enumerate(docs)]
    return {"type": t, "label": cfg["label"], "id": eid, "published_version": (ent or {}).get("published_version"),
            "latest": {**meta_out(docs[-1], cfg), "content": content_of(docs[-1])}, "history": list(reversed(history))}


# ---------- Validation ----------
def validate_shape(t: str, content: dict) -> dict:
    cfg = TYPES[t]
    content = content_of(content)
    errors = []
    for f, typ in cfg["fields"].items():
        v = content.get(f)
        if v is None or not isinstance(v, typ) or isinstance(v, bool):
            errors.append(f)
        elif typ is S and f in ("title", "name", "prompt", "code") and not v.strip():
            errors.append(f)
    if errors:
        raise HTTPException(400, f"Champs manquants ou invalides : {', '.join(errors)}.")
    return content


async def normalize(t: str, c: dict) -> dict:
    if t == "question":
        ids = [o.get("id") for o in c["options"] if isinstance(o, dict)]
        if len(ids) < 2 or len(set(ids)) != len(ids) or any(not o.get("text") for o in c["options"]):
            raise HTTPException(400, "Une question doit comporter au moins deux options avec un identifiant unique et un texte.")
        if not c["correct"] or not set(c["correct"]) <= set(ids):
            raise HTTPException(400, "Les bonnes réponses doivent correspondre à des options existantes.")
        if c["type"] not in ("single", "multiple") or (c["type"] == "single" and len(c["correct"]) != 1):
            raise HTTPException(400, "Type de question invalide (choix unique : une seule bonne réponse).")
        if not c["competencies"]:
            raise HTTPException(400, "Une question doit évaluer au moins une compétence.")
        c.setdefault("module_id", None)
    elif t == "concept":
        if c.get("primary_stage") not in c["stage_ids"]:
            c["primary_stage"] = c["stage_ids"][0] if c["stage_ids"] else None
    elif t == "course":
        pins = {}
        for mid in c["module_ids"]:
            ent = await db.modules.find_one({"_id": mid})
            pins[mid] = int(c["module_pins"].get(mid) or (ent or {}).get("published_version") or 1)
        c["module_pins"] = pins
        c["optional_module_ids"] = [m for m in c["optional_module_ids"] if m in c["module_ids"]]
    elif t == "pathway":
        for pc in c["pathway_courses"]:
            if not isinstance(pc, dict) or not pc.get("course_id"):
                raise HTTPException(400, "Chaque cours du parcours doit avoir un identifiant.")
            ent = await db.courses.find_one({"_id": pc["course_id"]})
            pc["course_version"] = int(pc.get("course_version") or (ent or {}).get("published_version") or 1)
            pc["group"] = pc.get("group") if pc.get("group") in ("mandatory", "optional") else "mandatory"
            pc["bridge"] = pc.get("bridge") or BRIDGE
        c["course_ids"] = [pc["course_id"] for pc in c["pathway_courses"]]
    elif t == "assessment":
        if c["kind"] not in ("formative", "graded", "diagnostic"):
            raise HTTPException(400, "Type d'évaluation invalide.")
        for q in c["questions"]:
            if not q.get("version"):
                ent = await db.question_bank.find_one({"_id": q.get("question_id")})
                q["version"] = (ent or {}).get("published_version") or 1
    elif t == "resource" and c["type"] == "Vidéo" and c.get("video_url") and not str(c["video_url"]).startswith("https://"):
        raise HTTPException(400, "L'URL de la vidéo doit commencer par https://")
    return c


async def ids_in(coll: str, published_only: bool = False) -> set:
    query = {"published_version": {"$nin": [None]}} if published_only else {}
    return {d["_id"] async for d in db[coll].find(query, {"_id": 1})}


async def find_cycle(t: str, eid: str, prereqs: List[str]) -> Optional[List[str]]:
    graph = {}
    if t == "concept":
        async for d in db.concepts.find({}, {"prerequisite_ids": 1}):
            graph[d["_id"]] = d.get("prerequisite_ids", [])
    else:
        async for e in db.modules.find({"published_version": {"$nin": [None]}}):
            v = await db.module_versions.find_one({"entity_id": e["_id"], "version": e["published_version"]})
            graph[e["_id"]] = (v or {}).get("prerequisite_module_ids", [])
    graph[eid] = prereqs
    stack, seen = [(p, [eid, p]) for p in prereqs], set()
    while stack:
        node, path = stack.pop()
        if node == eid:
            return path
        if node in seen:
            continue
        seen.add(node)
        stack.extend((n, path + [n]) for n in graph.get(node, []))
    return None


async def version_status(coll: str, eid: str, version) -> Optional[str]:
    d = await db[coll].find_one({"entity_id": eid, "version": version}, {"status": 1})
    return d["status"] if d else None


async def publish_errors(t: str, eid: str, c: dict) -> List[str]:
    errs = []
    comps, stages, layers = await ids_in("competencies"), await ids_in("stages"), await ids_in("layers")
    unknown = lambda items, known: [i for i in items if i not in known]  # noqa: E731
    if t == "concept":
        if not c["stage_ids"] or not c["layer_ids"]:
            errs.append("Une notion doit être rattachée à au moins une étape et une couche.")
        if unknown(c["stage_ids"], stages) or unknown(c["layer_ids"], layers):
            errs.append("Étape ou couche inconnue.")
        missing = [p for p in c["prerequisite_ids"] if p != eid and p not in await ids_in("concepts")]
        if missing:
            errs.append(f"Prérequis non publiés : {', '.join(missing)}.")
        mods = unknown(c["module_ids"], await ids_in("modules", True))
        if mods:
            errs.append(f"Modules liés non publiés : {', '.join(mods)}.")
        cycle = await find_cycle(t, eid, c["prerequisite_ids"])
        if cycle:
            errs.append(f"Cycle de prérequis détecté : {' → '.join(cycle)}.")
    elif t == "module":
        missing = unknown(c["prerequisite_module_ids"], await ids_in("modules", True))
        if missing:
            errs.append(f"Modules prérequis non publiés : {', '.join(missing)}.")
        res = unknown(c["resource_ids"], await ids_in("resources"))
        if res:
            errs.append(f"Ressources non publiées : {', '.join(res)}.")
        if unknown(c["competency_ids"], comps) or unknown(c["layer_ids"], layers) or unknown(c["stage_ids"], stages):
            errs.append("Compétence, couche ou étape inconnue.")
        cycle = await find_cycle(t, eid, c["prerequisite_module_ids"])
        if cycle:
            errs.append(f"Cycle de prérequis détecté : {' → '.join(cycle)}.")
    elif t == "resource":
        if not await db.module_versions.find_one({"entity_id": c["module_id"]}):
            errs.append(f"Module de rattachement inconnu : {c['module_id']}.")
    elif t == "question":
        if unknown([x.get("competency_id") for x in c["competencies"]], comps):
            errs.append("Compétence évaluée inconnue.")
    elif t == "assessment":
        for q in c["questions"]:
            if await version_status("questions", q.get("question_id"), q.get("version")) != "published":
                errs.append(f"Question non publiée : {q.get('question_id')} v{q.get('version')}.")
    elif t == "course":
        if not c["module_ids"]:
            errs.append("Un cours doit contenir au moins un module.")
        for mid, v in c["module_pins"].items():
            if await version_status("module_versions", mid, v) != "published":
                errs.append(f"Module {mid} v{v} non publié.")
    elif t == "pathway":
        for pc in c["pathway_courses"]:
            if await version_status("course_versions", pc["course_id"], pc["course_version"]) != "published":
                errs.append(f"Cours {pc['course_id']} v{pc['course_version']} non publié.")
        if unknown([x.get("competency_id") for x in c["target_competencies"]], comps):
            errs.append("Compétence cible inconnue.")
    elif t == "credential":
        published_mods = await ids_in("modules", True)
        for r in c["rules"]:
            if r.get("kind") == "assessment_passed":
                if not await db.assessments.find_one({"_id": r.get("assessment_id"), "kind": "graded"}):
                    errs.append(f"Règle {r.get('id')} : évaluation notée inconnue.")
                continue
            if r.get("competency_id") not in comps:
                errs.append(f"Règle {r.get('id')} : compétence inconnue.")
            if r.get("module_id") and r["module_id"] not in published_mods:
                errs.append(f"Règle {r.get('id')} : module {r['module_id']} non publié.")
    return errs


async def project(t: str, eid: str, content: dict, version: int):
    cfg, now = TYPES[t], now_iso()
    latest = (await latest_of(t, eid))["version"]
    if cfg.get("projection"):
        await db[cfg["entity"]].replace_one({"_id": eid}, {**content, "_id": eid, "version": version, "status": "published", "published_version": version,
                                                         "latest_version": latest, "updated_at": now}, upsert=True)
    else:
        fields = {k: content[k] for k in cfg.get("entity_fields", []) if k in content}
        await db[cfg["entity"]].update_one({"_id": eid}, {"$set": {"code": eid, **fields, "published_version": version, "latest_version": latest, "updated_at": now},
                                                          "$setOnInsert": {"created_at": now}}, upsert=True)


# ---------- Content & versions ----------
class CreateIn(BaseModel):
    id: Optional[str] = Field(None, max_length=60, pattern=r"^[A-Za-z0-9_-]+$")
    content: Dict[str, Any]
    changelog: str = Field("Création", max_length=500)


class SaveIn(BaseModel):
    content: Dict[str, Any]
    changelog: str = Field("Modification", max_length=500)


class ReviewIn(BaseModel):
    decision: str = Field(pattern="^(approve|return)$")
    comment: str = Field("", max_length=2000)


class RetireIn(BaseModel):
    version: Optional[int] = None
    reason: str = Field(min_length=3, max_length=500)


async def entity_index(t: str) -> List[dict]:
    cfg = TYPES[t]
    pipe = [{"$sort": {"version": 1}}, {"$group": {"_id": "$entity_id", "title": {"$last": f"${cfg['title']}"}, "module_id": {"$last": "$module_id"},
                                                   "latest_version": {"$last": "$version"}, "latest_status": {"$last": "$status"}, "approved": {"$last": "$approved"},
                                                   "versions": {"$push": {"version": "$version", "status": "$status"}}}}, {"$sort": {"_id": 1}}]
    pub = {d["_id"]: d.get("published_version") async for d in db[cfg["entity"]].find({}, {"published_version": 1})}
    return [{"id": d["_id"], "title": short(d["title"]), "module_id": d.get("module_id"), "latest_version": d["latest_version"], "latest_status": d["latest_status"],
             "approved": bool(d.get("approved")), "versions": d["versions"], "published_version": pub.get(d["_id"])}
            async for d in db[cfg["versions"]].aggregate(pipe)]


@router.get("/admin/content-types")
async def content_types(user: User = Depends(require_roles(*STAFF))):
    return [{"type": t, "label": c["label"], "can_edit": has(user, c["editors"])} for t, c in TYPES.items()]


@router.get("/admin/content/{t}")
async def list_content(t: str, q: Optional[str] = Query(None, max_length=120), status: Optional[str] = None, user: User = Depends(require_roles(*STAFF))):
    cfg_of(t)
    items = await entity_index(t)
    if q:
        items = [i for i in items if norm(q) in norm(f"{i['id']} {i['title']}")]
    if status:
        items = [i for i in items if i["latest_status"] == status]
    return items


@router.get("/admin/content/{t}/{eid}")
async def get_content(t: str, eid: str, user: User = Depends(require_roles(*STAFF))):
    cfg_of(t)
    return await detail(t, eid)


@router.post("/admin/content/{t}")
async def create_content(t: str, body: CreateIn, user: User = Depends(require_roles(*STAFF))):
    cfg = cfg_of(t)
    ensure(user, cfg["editors"])
    content = await normalize(t, validate_shape(t, body.content))
    eid = body.id or f"{cfg['prefix']}{slug(str(content.get(cfg['title'], '')))}"
    if await db[cfg["versions"]].find_one({"entity_id": eid}) or await entity_doc(t, eid):
        raise HTTPException(409, f"L'identifiant {eid} existe déjà.")
    doc = {"_id": f"{eid}@1", "entity_id": eid, "version": 1, "status": "draft", "approved": False, "changelog": body.changelog,
           "created_at": now_iso(), "created_by": who(user), "reviews": [], **content}
    if t == "question":
        doc["question_id"] = eid
    await db[cfg["versions"]].insert_one(doc)
    await log_change(user, t, eid, "create", f"Brouillon v1 créé : {short(content.get(cfg['title']))}", 1)
    return await detail(t, eid)


async def update_draft(t: str, doc: dict, content: dict, changelog: str, user: User):
    keep = {k: v for k, v in doc.items() if k in META}
    await db[TYPES[t]["versions"]].replace_one({"_id": doc["_id"]}, {**keep, **content, "changelog": changelog, "approved": False, "updated_at": now_iso()})
    changed = [c["field"] for c in diff(doc, content)]
    await log_change(user, t, doc["entity_id"], "update", f"Brouillon v{doc['version']} modifié ({', '.join(changed) or 'aucun champ'})", doc["version"])


async def write_draft(t: str, eid: str, content: dict, changelog: str, user: User):
    cfg = TYPES[t]
    docs = await versions_of(t, eid)
    cur = docs[-1] if docs else None
    if cur and cur["status"] == "review":
        raise HTTPException(409, f"La version v{cur['version']} est en relecture : elle doit être renvoyée en brouillon avant toute modification.")
    if cur and cur["status"] == "draft":
        return await update_draft(t, cur, content, changelog, user)
    n = cur["version"] + 1 if cur else 1
    doc = {"_id": f"{eid}@{n}", "entity_id": eid, "version": n, "status": "draft", "approved": False, "changelog": changelog,
           "created_at": now_iso(), "created_by": who(user), "reviews": [], **content}
    if t == "question":
        doc["question_id"] = eid
    await db[cfg["versions"]].insert_one(doc)
    await db[cfg["entity"]].update_one({"_id": eid}, {"$set": {"latest_version": n}})
    detail_txt = f"Nouvelle version brouillon v{n} créée à partir de v{cur['version']} ({cur['status']})" if cur else "Brouillon v1 créé"
    await log_change(user, t, eid, "new_version" if cur else "create", detail_txt, n)


@router.put("/admin/content/{t}/{eid}")
async def save_content(t: str, eid: str, body: SaveIn, user: User = Depends(require_roles(*STAFF))):
    cfg = cfg_of(t)
    ensure(user, cfg["editors"])
    content = await normalize(t, validate_shape(t, body.content))
    await latest_of(t, eid)
    await write_draft(t, eid, content, body.changelog, user)
    return await detail(t, eid)


@router.delete("/admin/versions/{t}/{eid}/{v}")
async def delete_draft(t: str, eid: str, v: int, user: User = Depends(require_roles(*STAFF))):
    cfg = cfg_of(t)
    doc = await db[cfg["versions"]].find_one({"entity_id": eid, "version": v})
    if not doc:
        raise HTTPException(404, "Version introuvable")
    if doc["status"] != "draft" or doc.get("published_at"):
        raise HTTPException(409, "Seul un brouillon jamais publié peut être supprimé.")
    if (doc.get("created_by") or {}).get("id") != user.id and not has(user, PUBLISHERS):
        raise HTTPException(403, "Seul l'auteur du brouillon, le responsable pédagogique ou l'administrateur peut le supprimer.")
    await db[cfg["versions"]].delete_one({"_id": doc["_id"]})
    rest = await versions_of(t, eid)
    if rest:
        await db[cfg["entity"]].update_one({"_id": eid}, {"$set": {"latest_version": rest[-1]["version"]}})
    await log_change(user, t, eid, "delete_draft", f"Brouillon v{v} supprimé", v)
    return await detail(t, eid) if rest else {"deleted": True, "id": eid}


@router.get("/admin/versions/{t}/{eid}")
async def version_history(t: str, eid: str, user: User = Depends(require_roles(*STAFF))):
    cfg_of(t)
    return (await detail(t, eid))["history"]


@router.get("/admin/versions/{t}/{eid}/{v}")
async def get_version(t: str, eid: str, v: int, user: User = Depends(require_roles(*STAFF))):
    cfg = cfg_of(t)
    doc = await db[cfg["versions"]].find_one({"entity_id": eid, "version": v})
    if not doc:
        raise HTTPException(404, "Version introuvable")
    return {**meta_out(doc, cfg), "content": content_of(doc)}


@router.put("/admin/versions/{t}/{eid}/{v}")
async def edit_version(t: str, eid: str, v: int, body: SaveIn, user: User = Depends(require_roles(*STAFF))):
    cfg = cfg_of(t)
    ensure(user, cfg["editors"])
    doc = await db[cfg["versions"]].find_one({"entity_id": eid, "version": v})
    if not doc:
        raise HTTPException(404, "Version introuvable")
    if doc["status"] in ("published", "retired"):
        raise HTTPException(409, f"La version v{v} est {'publiée' if doc['status'] == 'published' else 'retirée'} : elle est immuable. Toute modification crée une nouvelle version brouillon.")
    if doc["status"] == "review":
        raise HTTPException(409, f"La version v{v} est en relecture : elle doit être renvoyée en brouillon avant toute modification.")
    await update_draft(t, doc, await normalize(t, validate_shape(t, body.content)), body.changelog, user)
    return await detail(t, eid)


@router.post("/admin/versions/{t}/{eid}/submit")
async def submit_version(t: str, eid: str, user: User = Depends(require_roles(*STAFF))):
    cfg = cfg_of(t)
    ensure(user, cfg["editors"])
    cur = await latest_of(t, eid)
    if cur["status"] != "draft":
        raise HTTPException(409, "Seul un brouillon peut être soumis à relecture.")
    await db[cfg["versions"]].update_one({"_id": cur["_id"]}, {"$set": {"status": "review", "approved": False, "submitted_at": now_iso(), "submitted_by": who(user)}})
    await log_change(user, t, eid, "submit", f"v{cur['version']} soumise à relecture", cur["version"])
    return await detail(t, eid)


@router.post("/admin/versions/{t}/{eid}/review")
async def review_version(t: str, eid: str, body: ReviewIn, user: User = Depends(require_roles(*STAFF))):
    cfg = cfg_of(t)
    ensure(user, REVIEWERS, "Seul l'administrateur peut relire.")
    cur = await latest_of(t, eid)
    if cur["status"] != "review":
        raise HTTPException(409, "Aucune version en relecture pour ce contenu.")
    if body.decision == "return" and len(body.comment.strip()) < 3:
        raise HTTPException(400, "Un commentaire est obligatoire pour renvoyer une version à l'auteur.")
    entry = {"by": who(user), "at": now_iso(), "decision": body.decision, "comment": body.comment.strip()}
    update = {"approved": True} if body.decision == "approve" else {"status": "draft", "approved": False}
    await db[cfg["versions"]].update_one({"_id": cur["_id"]}, {"$set": update, "$push": {"reviews": entry}})
    label = "approuvée" if body.decision == "approve" else "renvoyée à l'auteur"
    await log_change(user, t, eid, "approve" if body.decision == "approve" else "return", f"v{cur['version']} {label}{' : ' + entry['comment'] if entry['comment'] else ''}", cur["version"])
    return await detail(t, eid)


@router.post("/admin/versions/{t}/{eid}/publish")
async def publish_version(t: str, eid: str, user: User = Depends(require_roles(*STAFF))):
    cfg = cfg_of(t)
    ensure(user, PUBLISHERS, "Seul l'administrateur peut publier.")
    cur = await latest_of(t, eid)
    if cur["status"] != "review" or not cur.get("approved"):
        raise HTTPException(409, "La version doit être approuvée en relecture avant publication.")
    content = content_of(cur)
    errs = await publish_errors(t, eid, content)
    if errs:
        await log_change(user, t, eid, "publish_blocked", " ".join(errs), cur["version"])
        raise HTTPException(422, "Publication bloquée : " + " ".join(errs))
    await db[cfg["versions"]].update_one({"_id": cur["_id"]}, {"$set": {"status": "published", "published_at": now_iso(), "published_by": who(user)}})
    await db[cfg["versions"]].update_many({"entity_id": eid, "status": "published", "version": {"$ne": cur["version"]}}, {"$set": {"superseded": True}})
    await project(t, eid, content, cur["version"])
    await log_change(user, t, eid, "publish", f"v{cur['version']} publiée", cur["version"])
    return await detail(t, eid)


@router.post("/admin/versions/{t}/{eid}/retire")
async def retire_version(t: str, eid: str, body: RetireIn, user: User = Depends(require_roles(*STAFF))):
    cfg = cfg_of(t)
    ensure(user, PUBLISHERS, "Seul l'administrateur peut retirer une version.")
    ent = await entity_doc(t, eid)
    v = body.version or (ent or {}).get("published_version")
    doc = await db[cfg["versions"]].find_one({"entity_id": eid, "version": v})
    if not doc or doc["status"] != "published":
        raise HTTPException(409, "Seule une version publiée peut être retirée.")
    await db[cfg["versions"]].update_one({"_id": doc["_id"]}, {"$set": {"status": "retired", "retired_at": now_iso(), "retired_by": who(user), "retire_reason": body.reason}})
    if ent and ent.get("published_version") == v:
        fallback = await db[cfg["versions"]].find_one({"entity_id": eid, "status": "published"}, sort=[("version", -1)])
        if fallback:
            await db[cfg["versions"]].update_one({"_id": fallback["_id"]}, {"$set": {"superseded": False}})
            await project(t, eid, content_of(fallback), fallback["version"])
        elif cfg.get("projection"):
            await db[cfg["entity"]].delete_one({"_id": eid})
        else:
            await db[cfg["entity"]].update_one({"_id": eid}, {"$set": {"published_version": None}})
    await log_change(user, t, eid, "retire", f"v{v} retirée : {body.reason}", v)
    return await detail(t, eid)


@router.get("/admin/review-queue")
async def review_queue(user: User = Depends(require_roles(*STAFF))):
    out = []
    for t, cfg in TYPES.items():
        async for d in db[cfg["versions"]].find({"status": "review"}).sort("submitted_at", 1):
            out.append({"type": t, "label": cfg["label"], **meta_out(d, cfg)})
    return out


@router.get("/admin/options")
async def options(user: User = Depends(require_roles(*STAFF))):
    pick = lambda docs, *f: [{k: d.get(k) for k in ("_id",) + f} | {"id": d["_id"]} for d in docs]  # noqa: E731
    out = {"roles": ROLES}
    for coll, fields in [("stages", ("code", "name")), ("layers", ("name",)), ("competencies", ("name",)), ("levels", ("name",)), ("profiles", ("name",))]:
        out[coll] = [{k: v for k, v in x.items() if k != "_id"} for x in pick(await db[coll].find().sort("order", 1).to_list(100), *fields)]
    for t in TYPES:
        out[t] = await entity_index(t)
    return out


@router.post("/admin/files")
async def upload_file(file: UploadFile = File(...), user: User = Depends(require_roles(*AUTHORS))):
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ext not in projects.ALLOWED:
        raise HTTPException(400, "Format non accepté : seuls les fichiers PDF et DOCX sont autorisés.")
    data = await file.read()
    if len(data) > projects.MAX_BYTES:
        raise HTTPException(400, "Fichier trop volumineux (10 Mo maximum).")
    path = f"{os.environ['STORAGE_APP_NAME']}/resources/{uuid.uuid4()}.{ext}"
    result = await run_in_threadpool(projects.put_object, path, data, projects.ALLOWED[ext])
    await log_change(user, "file", result["path"], "upload", file.filename)
    return {"storage_path": result["path"], "original_filename": file.filename, "content_type": projects.ALLOWED[ext], "size": len(data)}


# ---------- Change log ----------
@router.get("/admin/changelog")
async def changelog(entity_type: Optional[str] = None, action: Optional[str] = None, user_email: Optional[str] = None, entity_id: Optional[str] = None,
                    limit: int = Query(200, ge=1, le=1000), user: User = Depends(require_roles(*STAFF))):
    query = {k: v for k, v in {"entity_type": entity_type, "action": action, "user_email": user_email, "entity_id": entity_id}.items() if v}
    return [BaseDocument.from_mongo(d).out() async for d in db.catalog_change_log.find(query).sort("at", -1).limit(limit)]


# ---------- Users ----------
class UserCreateIn(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class UserPatchIn(BaseModel):
    active: Optional[bool] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=80)
    last_name: Optional[str] = Field(None, min_length=1, max_length=80)
    password: Optional[str] = Field(None, min_length=8, max_length=128)



def user_out(doc: dict) -> dict:
    u = User.from_mongo(doc).public()
    u["active"] = doc.get("active", True)
    u["legacy_roles"] = doc.get("legacy_roles", [])
    return u


@router.get("/admin/users")
async def list_users(q: Optional[str] = Query(None, max_length=120), role: Optional[str] = None, user: User = Depends(require_roles("admin"))):
    query = {"role": role} if role else {}
    docs = await db.users.find(query).sort("created_at", -1).to_list(2000)
    out = [user_out(d) for d in docs]
    if q:
        out = [u for u in out if norm(q) in norm(f"{u['email']} {u['first_name']} {u['last_name']}")]
    return out


@router.post("/admin/users")
async def create_user(body: UserCreateIn, user: User = Depends(require_roles("admin"))):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "Un compte existe déjà avec cette adresse e-mail.")
    doc = {"email": email, "first_name": body.first_name.strip(), "last_name": body.last_name.strip(), "role": "learner", "session_version": 0,
           "password_hash": hash_password(body.password), "active": True, "created_at": now_iso(), "created_by": user.id}
    res = await db.users.insert_one(doc)
    doc["_id"] = res.inserted_id
    await log_change(user, "user", email, "create", "Compte apprenant créé")
    return user_out(doc)


PATCH_FIELDS = set(UserPatchIn.model_fields)


async def update_user_body(request: Request) -> UserPatchIn:
    raw = await request.json()
    if not isinstance(raw, dict):
        raise HTTPException(400, "Corps de requête invalide.")
    bad = sorted(set(raw) - PATCH_FIELDS)
    if bad:
        raise HTTPException(400, f"Champ non autorisé : {', '.join(bad)}. Champs modifiables : {', '.join(sorted(PATCH_FIELDS))}.")
    try:
        return UserPatchIn(**raw)
    except ValidationError as e:
        raise HTTPException(400, f"Valeur invalide : {e.errors()[0]['loc'][0]}.")


@router.patch("/admin/users/{uid}")
async def update_user(uid: str, user: User = Depends(require_roles("admin")), body: UserPatchIn = Depends(update_user_body)):
    try:
        doc = await db.users.find_one({"_id": ObjectId(uid)})
    except InvalidId:
        doc = None
    if not doc:
        raise HTTPException(404, "Utilisateur introuvable")
    update, notes, bump = {}, [], False
    if doc.get("role") == "admin" and (body.active is False or body.password):
        raise HTTPException(400, "Le compte administrateur ne peut être ni désactivé ni réinitialisé depuis l'interface. Utilisez la procédure de récupération serveur.")
    if body.active is not None:
        bump = bump or body.active is False
        update["active"] = body.active
        notes.append("compte réactivé" if body.active else "compte désactivé")
    for f in ("first_name", "last_name"):
        if getattr(body, f):
            update[f] = getattr(body, f).strip()
            notes.append(f"{f} modifié")
    if body.password:
        update["password_hash"] = hash_password(body.password)
        notes.append("mot de passe provisoire défini")
        bump = True
    if update:
        await db.users.update_one({"_id": doc["_id"]}, {"$set": update, **({"$inc": {"session_version": 1}} if bump else {})})
        await log_change(user, "user", doc["email"], "update", " ; ".join(notes))
    return user_out(await db.users.find_one({"_id": doc["_id"]}))


# ---------- Analytics ----------
class EventIn(BaseModel):
    type: str = Field(pattern="^(demo_start|demo_complete|demo_layer_click)$")
    session_id: Optional[str] = Field(None, max_length=64)
    layer_id: Optional[str] = Field(None, max_length=60)
    step: Optional[int] = Field(None, ge=1, le=7)


@router.post("/events")
async def track_event(body: EventIn, user: Optional[User] = Depends(get_optional_user)):
    if user and user.role == "admin":
        return {"ok": True, "recorded": False}
    await db.events.insert_one({"type": body.type, "session_id": body.session_id, "layer_id": body.layer_id, "step": body.step,
                                "user_id": user.id if user else None, "at": now_iso()})
    return {"ok": True}


@router.get("/admin/analytics")
async def analytics(user: User = Depends(require_roles(*STAFF))):
    count = db.events.count_documents
    starts, completes, clicks = await count({"type": "demo_start"}), await count({"type": "demo_complete"}), await count({"type": "demo_layer_click"})
    layers = {d["_id"]: d["name"] async for d in db.layers.find({}, {"name": 1})}
    by_layer = [{"layer_id": d["_id"], "name": layers.get(d["_id"], d["_id"]), "count": d["n"]}
                async for d in db.events.aggregate([{"$match": {"type": "demo_layer_click"}}, {"$group": {"_id": "$layer_id", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}])]
    m01 = set(await db.resource_progress.distinct("user_id", {"module_id": "M01"})) | set(await db.attempts.distinct("user_id", {"module_id": "M01"}))
    graded, passed = await db.attempts.count_documents({"kind": "graded"}), await db.attempts.count_documents({"kind": "graded", "passed": True})
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    roles = {d["_id"]: d["n"] async for d in db.users.aggregate([{"$match": {"active": {"$ne": False}}}, {"$group": {"_id": "$role", "n": {"$sum": 1}}}])}
    questions = {"graded": 0, "formative": 0, "diagnostic": 0}
    async for a in db.assessments.find({"published_version": {"$ne": None}}):
        v = await db.assessment_versions.find_one({"entity_id": a["_id"], "version": a["published_version"]})
        if v:
            questions[v.get("kind", "other")] = questions.get(v.get("kind", "other"), 0) + len(v.get("questions", []))
    content = {}
    for t, cfg in TYPES.items():
        statuses = {d["_id"]: d["n"] async for d in db[cfg["versions"]].aggregate([{"$group": {"_id": "$status", "n": {"$sum": 1}}}])}
        content[t] = {"label": cfg["label"], **{s: statuses.get(s, 0) for s in ("draft", "review", "published", "retired")}}
    rate = lambda a, b: round(a / b, 4) if b else 0  # noqa: E731
    return {
        "demo": {"starts": starts, "completions": completes, "completion_rate": rate(completes, starts), "layer_clicks": clicks, "by_layer": by_layer},
        "learning": {"m01_starters": len(m01), "graded_attempts": graded, "graded_passed": passed, "success_rate": rate(passed, graded),
                     "module_completions": await db.module_completions.count_documents({}), "enrollments": await db.enrollments.count_documents({})},
        "questions": {**questions, "total": sum(questions.values()), "bank": await db.question_bank.count_documents({})},
        "users": {"total": await db.users.count_documents({}), "inactive": await db.users.count_documents({"active": False}), "registrations_30d": await db.users.count_documents({"created_at": {"$gte": since}}), "by_role": roles},
        "credentials": {"catalog": await db.credentials.count_documents({"published_version": {"$ne": None}}), "issued": await db.awards.count_documents({}), "valid": await db.awards.count_documents({"status": "valid"}),
                        "revoked": await db.awards.count_documents({"status": "revoked"})},
        "projects": {s: await db.submissions.count_documents({"status": s}) for s in ("submitted", "validated", "rejected")},
        "content": content,
    }


# ---------- Migration (idempotent) ----------
async def migrate():
    await db.questions.update_many({"entity_id": {"$exists": False}}, [{"$set": {"entity_id": "$question_id"}}])
    for cfg in TYPES.values():
        await db[cfg["versions"]].create_index([("entity_id", 1), ("version", 1)], unique=True)
    await db.catalog_change_log.create_index([("at", -1)])
    await db.events.create_index("type")
    async for q in db.questions.find({"status": "published"}):
        await db.question_bank.update_one({"_id": q["question_id"]}, {"$setOnInsert": {"code": q["question_id"], "module_id": q.get("module_id"), "published_version": q["version"],
                                                                                      "latest_version": q["version"], "created_at": q.get("created_at", now_iso())}}, upsert=True)
    async for a in db.assessments.find():
        await db.assessment_versions.update_many({"entity_id": a["_id"], "title": {"$exists": False}},
                                                 {"$set": {k: a[k] for k in ("code", "kind", "module_id", "title", "pass_threshold", "max_attempts")}})
    async for cv in db.course_versions.find({"module_pins": {"$exists": False}}):
        await db.course_versions.update_one({"_id": cv["_id"]}, {"$set": {"module_pins": {m: 1 for m in cv["module_ids"]}, "optional_module_ids": []}})
    async for pv in db.pathway_versions.find({"pathway_courses.course_version": {"$exists": False}}):
        pcs = [{**pc, "course_version": pc.get("course_version", 1)} for pc in pv["pathway_courses"]]
        await db.pathway_versions.update_one({"_id": pv["_id"]}, {"$set": {"pathway_courses": pcs}})
    for t in ("concept", "resource", "credential"):
        cfg = TYPES[t]
        async for e in db[cfg["entity"]].find():
            v = e.get("version", 1)
            content = content_of(e)
            if not await db[cfg["versions"]].find_one({"entity_id": e["_id"]}):
                await db[cfg["versions"]].insert_one({"_id": f"{e['_id']}@{v}", "entity_id": e["_id"], "version": v, "status": "published", "approved": True,
                                                      "changelog": "Version initiale", "created_at": e.get("created_at", "2026-09-01T00:00:00+00:00"),
                                                      "published_at": "2026-09-01T00:00:00+00:00", "reviews": [], **content})
            if "published_version" not in e:
                await db[cfg["entity"]].update_one({"_id": e["_id"]}, {"$set": {"published_version": v, "latest_version": v, "version": v, "status": "published"}})
