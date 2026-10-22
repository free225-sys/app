import os
import uuid
from typing import Dict, Optional

import requests
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from auth import User, get_current_user, require_learner, require_roles
from core import BaseDocument, db, logger, now_iso

router = APIRouter(prefix="/api", tags=["projects"])

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
MAX_BYTES = 10 * 1024 * 1024
ALLOWED = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
REVIEWERS = ("admin",)
_storage_key = None


def init_storage(force: bool = False):
    global _storage_key
    if os.environ.get("STORAGE_DISABLED") == "1":
        raise RuntimeError("stockage objet désactivé sur cette instance")
    if _storage_key and not force:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": os.environ["EMERGENT_LLM_KEY"]}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    resp = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage(), "Content-Type": content_type}, data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage()}, timeout=60)
    if resp.status_code == 404:
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage(force=True)}, timeout=60)
    resp.raise_for_status()
    return resp.content


def startup_storage():
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")


async def get_rubric(module_id: str) -> dict:
    doc = await db.rubrics.find_one({"module_id": module_id, "status": "published"}, sort=[("version", -1)])
    if not doc:
        raise HTTPException(404, "Aucun projet pour ce module")
    return BaseDocument.from_mongo(doc).out()


def submission_out(doc: dict, with_user: Optional[dict] = None) -> dict:
    s = BaseDocument.from_mongo(doc).out()
    if s.get("file"):
        s["file"] = {k: s["file"][k] for k in ["original_filename", "content_type", "size"]}
    if with_user:
        s["learner"] = {"first_name": with_user["first_name"], "last_name": with_user["last_name"], "email": with_user["email"]}
    return s


async def load_submission(sid: str) -> dict:
    try:
        doc = await db.submissions.find_one({"_id": ObjectId(sid)})
    except InvalidId:
        doc = None
    if not doc:
        raise HTTPException(404, "Soumission introuvable")
    return doc


@router.get("/projects/{module_id}/rubric")
async def rubric(module_id: str):
    return await get_rubric(module_id)


@router.post("/projects/{module_id}/submissions")
async def submit_project(module_id: str, title: str = Form(..., min_length=3, max_length=160), description: str = Form(..., min_length=50, max_length=20000),
                         file: Optional[UploadFile] = File(None), user: User = Depends(require_learner)):
    rub = await get_rubric(module_id)
    if await db.submissions.find_one({"user_id": user.id, "module_id": module_id, "status": {"$in": ["submitted", "validated"]}}):
        raise HTTPException(409, "Une soumission est déjà en attente d'évaluation ou validée pour ce projet.")
    file_ref = None
    if file and file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED:
            raise HTTPException(400, "Format non accepté : seuls les fichiers PDF et DOCX sont autorisés.")
        data = await file.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(400, "Fichier trop volumineux (10 Mo maximum).")
        path = f"{os.environ['STORAGE_APP_NAME']}/projects/{user.id}/{uuid.uuid4()}.{ext}"
        result = await run_in_threadpool(put_object, path, data, ALLOWED[ext])
        file_ref = {"storage_path": result["path"], "original_filename": file.filename, "content_type": ALLOWED[ext], "size": len(data), "is_deleted": False}
    doc = {"user_id": user.id, "module_id": module_id, "rubric_id": rub["rubric_id"], "rubric_version": rub["version"], "title": title.strip(),
           "description": description.strip(), "file": file_ref, "status": "submitted", "submitted_at": now_iso(), "review": None}
    res = await db.submissions.insert_one(doc)
    doc["_id"] = res.inserted_id
    return submission_out(doc)


@router.get("/learners/me/submissions")
async def my_submissions(user: User = Depends(require_learner)):
    return [submission_out(d) async for d in db.submissions.find({"user_id": user.id}).sort("submitted_at", -1)]


@router.get("/projects/submissions/{sid}/file")
async def submission_file(sid: str, user: User = Depends(get_current_user)):
    doc = await load_submission(sid)
    if doc["user_id"] != user.id and user.role != "admin":
        raise HTTPException(403, "Accès réservé.")
    if not doc.get("file") or doc["file"].get("is_deleted"):
        raise HTTPException(404, "Aucun fichier joint")
    data = await run_in_threadpool(get_object, doc["file"]["storage_path"])
    return Response(content=data, media_type=doc["file"]["content_type"],
                    headers={"Content-Disposition": f'attachment; filename="projet-{sid}.{doc["file"]["storage_path"].rsplit(".", 1)[-1]}"'})


@router.get("/evaluation/submissions")
async def list_for_evaluation(status: Optional[str] = Query(None), user: User = Depends(require_roles(*REVIEWERS))):
    query = {"status": status} if status else {}
    out = []
    async for d in db.submissions.find(query).sort("submitted_at", 1):
        learner = await db.users.find_one({"_id": ObjectId(d["user_id"])})
        out.append(submission_out(d, learner))
    return out


class ReviewIn(BaseModel):
    scores: Dict[str, int]
    comment: str = Field(min_length=10, max_length=5000)
    decision: str = Field(pattern="^(validated|rejected)$")


@router.post("/evaluation/submissions/{sid}/review")
async def review_submission(sid: str, body: ReviewIn, user: User = Depends(require_roles(*REVIEWERS))):
    doc = await load_submission(sid)
    if doc["status"] != "submitted":
        raise HTTPException(409, "Cette soumission a déjà été évaluée.")
    rub = BaseDocument.from_mongo(await db.rubrics.find_one({"rubric_id": doc["rubric_id"], "version": doc["rubric_version"]})).out()
    max_score = max(lv["score"] for lv in rub["levels"])
    crit_ids = [c["id"] for c in rub["criteria"]]
    if set(body.scores) != set(crit_ids) or any(not 0 <= v <= max_score for v in body.scores.values()):
        raise HTTPException(400, "Chaque critère de la grille doit recevoir un niveau valide.")
    total = sum(c["weight"] * max_score for c in rub["criteria"])
    percent = round(sum(c["weight"] * body.scores[c["id"]] for c in rub["criteria"]) / total, 4)
    if body.decision == "validated" and percent < rub["pass_threshold"]:
        raise HTTPException(400, f"Score insuffisant pour valider ({round(percent * 100)} % < {round(rub['pass_threshold'] * 100)} %).")
    review = {"evaluator_id": user.id, "evaluator_name": f"{user.first_name} {user.last_name}", "scores": body.scores, "percent": percent,
              "comment": body.comment.strip(), "decision": body.decision, "reviewed_at": now_iso()}
    await db.submissions.update_one({"_id": doc["_id"]}, {"$set": {"status": body.decision, "review": review}})
    if body.decision == "validated":
        for cid in rub["competency_ids"]:
            key = {"user_id": doc["user_id"], "competency_id": cid, "module_id": doc["module_id"], "evidence_type": "project"}
            await db.attainments.update_one(key, {"$set": {**key, "level": rub["level"], "score_percent": percent, "acquired_at": review["reviewed_at"], "status": "valid",
                                                           "evidence": {"type": "project", "submission_id": sid, "rubric_id": rub["rubric_id"],
                                                                        "rubric_version": rub["version"], "evaluator_id": user.id}}}, upsert=True)
    return submission_out(await load_submission(sid))
