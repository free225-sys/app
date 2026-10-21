"""Read-only export of the review queue (drafts and versions in review) as Markdown or PDF."""
import json
import re
from datetime import datetime, timezone
from io import BytesIO
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

import certificates  # noqa: F401  (registers Inter fonts)
from admin import TYPES, content_of
from auth import User, require_roles
from core import db
from learning import ATTAIN_THRESHOLD

router = APIRouter(prefix="/api")
ORDER = ["question", "assessment", "module", "course", "pathway"]
STATUS = {"draft": "brouillon", "review": "en relecture"}
registerFontFamily("Inter", normal="Inter", bold="Inter-SemiBold", italic="Inter", boldItalic="Inter-SemiBold")


def full(v) -> str:
    return "—" if v in (None, "", [], {}) else (v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))


async def published_version(t: str, eid: str) -> Optional[int]:
    ent = await db[TYPES[t]["entity"]].find_one({"_id": eid}, {"published_version": 1})
    return (ent or {}).get("published_version")


def references(t: str, c: dict) -> List[Tuple[str, str, Optional[int]]]:
    if t == "assessment":
        return [("question", q["question_id"], q.get("version")) for q in c.get("questions", [])]
    if t == "module":
        return [("assessment", a, None) for a in c.get("assessment_ids", [])] + [("resource", r, None) for r in c.get("resource_ids", [])]
    if t == "course":
        return [("module", m, v) for m, v in (c.get("module_pins") or {}).items()]
    if t == "pathway":
        return [("course", pc["course_id"], pc.get("course_version")) for pc in c.get("pathway_courses", [])]
    return []


async def collect() -> List[dict]:
    items = []
    for t in ORDER:
        async for v in db[TYPES[t]["versions"]].find({"status": {"$in": ["draft", "review"]}}).sort("entity_id", 1):
            pv = await published_version(t, v["entity_id"])
            prev = await db[TYPES[t]["versions"]].find_one({"entity_id": v["entity_id"], "version": pv}) if pv else None
            items.append({"type": t, "doc": v, "content": content_of(v), "published": pv, "prev": content_of(prev) if prev else None})
    pending = {(i["type"], i["doc"]["entity_id"]): i["doc"]["version"] for i in items}
    for i in items:
        deps, before = [], []
        for rt, rid, rv in references(i["type"], i["content"]):
            pub = await published_version(rt, rid) if rt in TYPES else None
            label = f"{rid}" + (f" v{rv}" if rv else "")
            pub_txt = f"v{pub}" if pub else "aucune"
            deps.append(f"{TYPES[rt]['label'] if rt in TYPES else rt} {label} (publiée : {pub_txt})")
            if (rt, rid) in pending and (rv is None or rv == pending[(rt, rid)]) and (pub is None or (rv or 0) > pub):
                before.append(f"{rid} v{pending[(rt, rid)]}")
        i["deps"], i["before"] = deps, before
    return items


def last_revision(doc: dict) -> str:
    events = [(doc.get("created_at"), doc.get("created_by")), (doc.get("updated_at"), doc.get("updated_by")), (doc.get("submitted_at"), doc.get("submitted_by"))]
    events += [(r.get("at"), r.get("by")) for r in doc.get("reviews") or []]
    at, by = max((e for e in events if e[0]), key=lambda e: e[0])
    return f"{at[:16].replace('T', ' ')} UTC — {(by or {}).get('name', '?')} ({(by or {}).get('email', '?')})"


def question_block(c: dict) -> List[str]:
    lines = [f"- **Énoncé** : {c.get('prompt')}", f"- **Type** : {'choix multiple' if c.get('type') == 'multiple' else 'choix unique'}", "- **Choix** :"]
    for o in c.get("options", []):
        lines.append(f"  - {o['id']}) {o['text']}" + ("  **[bonne réponse]**" if o["id"] in c.get("correct", []) else ""))
    lines += [f"- **Bonne(s) réponse(s)** : {', '.join(c.get('correct', []))}", f"- **Explication** : {c.get('explanation')}",
              "- **Poids** : " + ", ".join(f"{w['competency_id']} × {w['weight']}" for w in c.get("competencies", [])), "- **Sources** :"]
    lines += [f"  - {s.get('resource_id')} : « {s.get('quote')} »" for s in c.get("sources") or []] or ["  - —"]
    lines.append(f"- **Note sur la source** : {c.get('source_note') or '—'}")
    return lines


async def scoring_block(items: List[dict]) -> List[str]:
    out = ["## Barème et règles"]
    for i in items:
        if i["type"] != "assessment":
            continue
        c = i["content"]
        weights = {}
        for q in c.get("questions", []):
            qd = await db.questions.find_one({"question_id": q["question_id"], "version": q.get("version")}) or {}
            for w in qd.get("competencies", []):
                weights[w["competency_id"]] = weights.get(w["competency_id"], 0) + w["weight"]
        mod = next((m for m in items if m["type"] == "module" and m["doc"]["entity_id"] == c.get("module_id")), None)
        level = (mod["content"].get("levels") or ["?"])[-1] if mod else "niveau de la version publiée du module"
        out += [f"### {i['doc']['entity_id']} v{i['doc']['version']}",
                f"- Seuil de réussite : {round(c.get('pass_threshold', 0) * 100)} % du nombre de questions ({len(c.get('questions', []))} questions) ; tentatives : {c.get('max_attempts')}.",
                "- Correction tout-ou-rien par question, choix multiples compris : une question n'est juste que si l'ensemble coché est exactement l'ensemble attendu.",
                "- Acquis : " + "; ".join(f"{k} pondéré sur {v} points, acquis si ≥ {round(ATTAIN_THRESHOLD * 100)} %" for k, v in weights.items())
                + ", calculé uniquement pour une tentative réussie.",
                f"- Niveau de l'acquis : niveau maximal du module publié au moment de la réussite ({c.get('module_id')} v{mod['doc']['version'] if mod else '?'} : {level})."]
    for m in items:
        if m["type"] == "module":
            rule = m["content"].get("completion_rule")
            out.append(f"- Règle de fin de {m['doc']['entity_id']} v{m['doc']['version']} : "
                       + ("ressources lues ET quiz noté réussi." if rule != "resources" else "ressources lues.") + f" (completion_rule = {rule}) — complétions existantes conservées, sans recalcul.")
    return out


async def build_markdown() -> str:
    items = await collect()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    md = ["# Document de relecture — préproduction — aucune publication", "", f"Généré le {now} depuis la base, en lecture seule. {len(items)} élément(s) en brouillon ou en relecture.", ""]
    md += ["## Ordre de publication"] + [f"{n}. {TYPES[i['type']]['label']} {i['doc']['entity_id']} v{i['doc']['version']}" for n, i in enumerate(items, 1)] + [""]
    md += await scoring_block(items) + [""]
    for i in items:
        d, c, t = i["doc"], i["content"], i["type"]
        md += [f"## {TYPES[t]['label']} {d['entity_id']} — brouillon v{d['version']}", "",
               f"- **Type** : {TYPES[t]['label']}", "- **Version publiée actuelle** : " + (f"v{i['published']}" if i["published"] else "aucune (nouvelle entité)"),
               f"- **Statut** : {STATUS.get(d['status'], d['status'])}, approuvée : {'oui' if d.get('approved') else 'non'}",
               f"- **Dernière révision** : {last_revision(d)}", f"- **Note de version** : {d.get('changelog') or '—'}",
               "- **Dépendances** : " + ("; ".join(i["deps"]) or "aucune"), "- **À publier avant** : " + (", ".join(i["before"]) or "rien"), ""]
        if t == "question":
            md += question_block(c) + [""]
        md.append("**Changements par rapport à la version publiée**" if i["prev"] else "**Changements : nouvelle entité** (contenu complet " + ("ci-dessus)" if t == "question" else "ci-dessous)"))
        keys = sorted(set(c) | set(i["prev"] or {}))
        for k in keys:
            a, b = (i["prev"] or {}).get(k), c.get(k)
            if i["prev"] is None:
                if t != "question":
                    md.append(f"- {k} : {full(b)}")
            elif a != b:
                md.append(f"- {k} : {full(a)} → {full(b)}")
        md.append("")
    return "\n".join(md)


def inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)


def to_pdf(md: str) -> bytes:
    base = ParagraphStyle("b", fontName="Inter", fontSize=9, leading=13)
    styles = {"# ": ParagraphStyle("h1", parent=base, fontName="Inter-SemiBold", fontSize=15, leading=19, spaceAfter=6),
              "## ": ParagraphStyle("h2", parent=base, fontName="Inter-SemiBold", fontSize=12, leading=16, spaceBefore=10, spaceAfter=4),
              "### ": ParagraphStyle("h3", parent=base, fontName="Inter-SemiBold", fontSize=10, leading=14, spaceBefore=6)}
    flow = []
    for line in md.split("\n"):
        if not line.strip():
            flow.append(Spacer(1, 4))
            continue
        head = next((p for p in ("### ", "## ", "# ") if line.startswith(p)), None)
        if head:
            flow.append(Paragraph(inline(line[len(head):]), styles[head]))
            continue
        indent = (len(line) - len(line.lstrip())) // 2
        body = line.strip()
        bullet = body.startswith("- ")
        flow.append(Paragraph(inline(body[2:] if bullet else body), ParagraphStyle("li", parent=base, leftIndent=10 + indent * 12, bulletIndent=indent * 12) if bullet else base,
                              bulletText="•" if bullet else None))
    buf = BytesIO()
    footer = "Document de relecture — préproduction — aucune publication"

    def on_page(canvas, doc):
        canvas.setFont("Inter", 7)
        canvas.drawString(18 * mm, 10 * mm, f"{footer} — page {doc.page}")
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                      title="File de relecture — CASA AI Academy").build(flow, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


@router.get("/admin/review-queue/export")
async def export_review_queue(format: str = Query("md", pattern="^(md|pdf)$"), user: User = Depends(require_roles("admin"))):
    md = await build_markdown()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    if format == "pdf":
        return Response(to_pdf(md), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="file-de-relecture-{stamp}.pdf"'})
    return Response(md, media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="file-de-relecture-{stamp}.md"'})
