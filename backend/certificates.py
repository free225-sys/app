from pathlib import Path
import io
import os
import secrets
from typing import List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from auth import User, get_current_user, require_roles
from core import BaseDocument, LEVEL_ORDER, all_docs, db, log_change, now_iso

router = APIRouter(prefix="/api", tags=["certificates"])
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class ReasonIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


def new_code() -> str:
    part = lambda: "".join(secrets.choice(CODE_ALPHABET) for _ in range(4))  # noqa: E731
    return f"CASA-{part()}-{part()}"


def rule_match(rule: dict, atts: List[dict]) -> Optional[dict]:
    for a in sorted(atts, key=lambda a: -a["score_percent"]):
        if (a["competency_id"] == rule["competency_id"] and a["evidence_type"] in rule["evidence_types"]
                and (not rule.get("module_id") or a["module_id"] == rule["module_id"])
                and LEVEL_ORDER.index(a["level"]) >= LEVEL_ORDER.index(rule["min_level"]) and a["score_percent"] >= rule["min_score"]):
            return a
    return None


async def evaluate(user_id: str, cred: dict) -> dict:
    atts = await db.attainments.find({"user_id": user_id, "status": "valid"}).to_list(1000)
    rules = []
    for r in cred["rules"]:
        if r.get("kind") == "assessment_passed":
            att = await db.attempts.find_one({"user_id": user_id, "assessment_id": r["assessment_id"], "passed": True}, sort=[("percent", -1)])
            rules.append({**r, "met": bool(att), "evidence": {"attempt_id": str(att["_id"]), "attainment_id": None, "evidence_type": "graded_attempt", "module_id": att["module_id"],
                                                               "score_percent": att["percent"], "acquired_at": att["created_at"]} if att else None})
            continue
        a = rule_match(r, atts)
        rules.append({**r, "met": bool(a), "evidence": {"attainment_id": str(a["_id"]), "evidence_type": a["evidence_type"], "module_id": a["module_id"],
                                                         "score_percent": a["score_percent"], "acquired_at": a["acquired_at"]} if a else None})
    met = sum(r["met"] for r in rules)
    return {"rules": rules, "met_count": met, "total": len(rules), "eligible": met == len(rules)}


def award_out(doc: dict) -> dict:
    a = BaseDocument.from_mongo(doc).out()
    a["verification_url"] = f"{os.environ['PUBLIC_APP_URL']}/verifier/{a['code']}"
    return a


async def get_credential(cid: str) -> dict:
    doc = await db.credentials.find_one({"_id": cid, "status": "published"})
    if not doc:
        raise HTTPException(404, "Certification introuvable")
    return BaseDocument.from_mongo(doc).out()


@router.get("/credentials")
async def list_credentials():
    return [c for c in await all_docs("credentials", "_id") if c["status"] == "published"]


@router.get("/learners/me/credentials")
async def my_credentials(user: User = Depends(get_current_user)):
    out = []
    for cred in await list_credentials():
        award = await db.awards.find_one({"user_id": user.id, "credential_id": cred["id"]}, sort=[("issued_at", -1)])
        out.append({"credential": {k: cred[k] for k in ["id", "title", "summary", "version"]}, **await evaluate(user.id, cred),
                    "award": award_out(award) if award else None})
    return out


@router.post("/credentials/{cid}/claim")
async def claim(cid: str, user: User = Depends(get_current_user)):
    cred = await get_credential(cid)
    existing = await db.awards.find_one({"user_id": user.id, "credential_id": cid, "status": "valid"})
    if existing:
        return award_out(existing)
    ev = await evaluate(user.id, cred)
    if not ev["eligible"]:
        raise HTTPException(400, f"Conditions non remplies : {ev['met_count']}/{ev['total']} preuves validées.")
    doc = {"code": new_code(), "user_id": user.id, "holder_name": f"{user.first_name} {user.last_name}", "credential_id": cid,
           "credential_version": cred["version"], "credential_title": cred["title"], "issued_at": now_iso(), "status": "valid",
           "revoked_at": None, "revoke_reason": None,
           "evidence_refs": [{"rule_id": r["id"], "label": r["label"], **r["evidence"]} for r in ev["rules"]]}
    res = await db.awards.insert_one(doc)
    doc["_id"] = res.inserted_id
    return award_out(doc)


LOGO = str(Path(__file__).parent / "assets" / "logo-casa.png")
FONTS = Path(__file__).parent / "assets" / "fonts"
pdfmetrics.registerFont(TTFont("Inter", str(FONTS / "Inter-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Inter-SemiBold", str(FONTS / "Inter-SemiBold.ttf")))


def render_pdf(a: dict) -> bytes:
    buf = io.BytesIO()
    w, h = landscape(A4)
    c = canvas.Canvas(buf, pagesize=(w, h))
    navy, green, muted, line = HexColor("#14243c"), HexColor("#147c77"), HexColor("#627086"), HexColor("#e5e9ef")
    c.setFillColor(HexColor("#f7f8fa"))
    c.rect(0, 0, w, h, stroke=0, fill=1)
    c.setStrokeColor(line)
    c.rect(28, 28, w - 56, h - 56, stroke=1, fill=0)
    lw = 64 * 1400 / 963
    c.drawImage(LOGO, 64, h - 124, width=lw, height=64, mask="auto")
    c.setFillColor(HexColor("#e8e9f7"))
    c.roundRect(64 + lw + 10, h - 101, 92, 20, 5, stroke=0, fill=1)
    c.setFillColor(HexColor("#5845ba"))
    c.setFont("Inter-SemiBold", 10)
    c.drawString(64 + lw + 18, h - 94, "AI ACADEMY")
    c.setFillColor(green)
    c.setFont("Inter-SemiBold", 10)
    c.drawString(64, h - 170, "CERTIFICAT")
    c.setFillColor(navy)
    c.setFont("Inter-SemiBold", 30)
    c.drawString(64, h - 210, a["credential_title"])
    c.setFont("Helvetica", 12)
    c.setFillColor(muted)
    c.drawString(64, h - 250, "Décerné à")
    c.setFillColor(navy)
    c.setFont("Inter-SemiBold", 24)
    c.drawString(64, h - 282, a["holder_name"])
    c.setFont("Helvetica", 11)
    c.setFillColor(muted)
    c.drawString(64, h - 316, "Sur la base des preuves de compétences suivantes :")
    c.setFillColor(navy)
    y = h - 338
    for ref in a["evidence_refs"]:
        c.drawString(76, y, f"—  {ref['label']}  ({round(ref['score_percent'] * 100)} %)")
        y -= 18
    issued = a["issued_at"][:10].split("-")
    c.setStrokeColor(line)
    c.line(64, 150, w - 64, 150)
    for x, label, value in [(64, "Date de délivrance", f"{issued[2]}/{issued[1]}/{issued[0]}"), (260, "Code de vérification", a["code"]),
                            (480, "Vérifier en ligne", a["verification_url"])]:
        c.setFont("Helvetica", 9)
        c.setFillColor(muted)
        c.drawString(x, 128, label)
        c.setFont("Helvetica-Bold" if x < 480 else "Helvetica", 11 if x < 480 else 9)
        c.setFillColor(navy)
        c.drawString(x, 112, value)
    c.setFont("Helvetica", 9)
    c.setFillColor(muted)
    c.drawString(64, 52, "CASA AI Academy — by")
    x0 = 64 + c.stringWidth("CASA AI Academy — by ", "Helvetica", 9)
    c.setFillColor(HexColor("#365ac8"))
    c.drawString(x0, 52, "Relais IT")
    c.linkURL("https://www.relaisit.com", (x0, 48, x0 + c.stringWidth("Relais IT", "Helvetica", 9), 62), relative=0)
    c.setFillColor(muted)
    c.drawRightString(w - 64, 52, f"Certification {a['credential_id']} · version {a['credential_version']}")
    c.showPage()
    c.save()
    return buf.getvalue()


@router.get("/certificates/{code}/pdf")
async def certificate_pdf(code: str, user: User = Depends(get_current_user)):
    doc = await db.awards.find_one({"code": code})
    if not doc or (doc["user_id"] != user.id and "admin" not in user.roles):
        raise HTTPException(404, "Certificat introuvable")
    if doc["status"] != "valid":
        raise HTTPException(410, "Ce certificat a été révoqué.")
    return Response(content=render_pdf(award_out(doc)), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="certificat-{code}.pdf"'})


@router.get("/verify/{code}")
async def verify(code: str):
    doc = await db.awards.find_one({"code": code.strip().upper()})
    if not doc:
        return {"status": "not_found", "code": code}
    return {"status": doc["status"], "code": doc["code"], "holder_name": doc["holder_name"], "credential_title": doc["credential_title"],
            "credential_id": doc["credential_id"], "issued_at": doc["issued_at"], "revoked_at": doc["revoked_at"], "revoke_reason": doc["revoke_reason"],
            "evidence": [{"label": r["label"], "evidence_type": r["evidence_type"]} for r in doc["evidence_refs"]]}


@router.get("/admin/certificates")
async def admin_list(user: User = Depends(require_roles("admin"))):
    return [award_out(d) async for d in db.awards.find().sort("issued_at", -1)]


@router.get("/admin/attainments")
async def admin_attainments(user: User = Depends(require_roles("admin"))):
    users = {str(u["_id"]): u async for u in db.users.find({}, {"email": 1, "first_name": 1, "last_name": 1})}
    out = []
    async for d in db.attainments.find().sort("acquired_at", -1).limit(500):
        a = BaseDocument.from_mongo(d).out()
        u = users.get(a["user_id"], {})
        a["learner"] = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or u.get("email")
        out.append(a)
    return out


async def revoke_award(doc: dict, reason: str):
    await db.awards.update_one({"_id": doc["_id"]}, {"$set": {"status": "revoked", "revoked_at": now_iso(), "revoke_reason": reason}})


@router.post("/admin/certificates/{code}/revoke")
async def admin_revoke(code: str, body: ReasonIn, user: User = Depends(require_roles("admin"))):
    doc = await db.awards.find_one({"code": code})
    if not doc:
        raise HTTPException(404, "Certificat introuvable")
    if doc["status"] == "valid":
        await revoke_award(doc, body.reason)
        await log_change(user, "certificate", code, "revoke", body.reason)
    return award_out(await db.awards.find_one({"_id": doc["_id"]}))


@router.post("/admin/attainments/{aid}/invalidate")
async def admin_invalidate(aid: str, body: ReasonIn, user: User = Depends(require_roles("admin"))):
    try:
        oid = ObjectId(aid)
    except InvalidId:
        raise HTTPException(404, "Preuve introuvable")
    res = await db.attainments.update_one({"_id": oid}, {"$set": {"status": "invalidated", "invalidated_at": now_iso(), "invalidation_reason": body.reason}})
    if not res.matched_count:
        raise HTTPException(404, "Preuve introuvable")
    revoked = []
    async for d in db.awards.find({"status": "valid", "evidence_refs.attainment_id": aid}):
        await revoke_award(d, f"Preuve invalidée : {body.reason}")
        revoked.append(d["code"])
    await log_change(user, "attainment", aid, "invalidate", f"{body.reason} — certificats révoqués : {', '.join(revoked) or 'aucun'}")
    return {"attainment_id": aid, "status": "invalidated", "revoked_certificates": revoked}
