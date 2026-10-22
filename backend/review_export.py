"""Read-only export of the review queue (drafts and versions in review) as Markdown or PDF."""
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from io import BytesIO
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

import certificates  # noqa: F401  (registers Inter fonts)
from admin import TYPES, content_of, credential_regressions
from auth import User, require_roles
from core import LEVEL_ORDER, db
from learning import ATTAIN_THRESHOLD

router = APIRouter(prefix="/api")
BASELINES = Path(__file__).parent / "data" / "review_baselines"
MEMORY = Path(__file__).resolve().parents[1] / "memory"
REPORTS = {"tableau-de-bord": ("RAPPORT_CORRECTION_TABLEAU_DE_BORD.md", "Correction du tableau de bord"),
           "test-isole-cert-doc-01": ("RAPPORT_TEST_ISOLE_CERT_DOC_01.md", "Tests isolés CERT-DOC-01"),
           "rapprochement-m001-v2": ("RAPPROCHEMENT_M001_V2.md", "Rapprochement M-001 v2"),
           "test-isole-regles-2026-10": ("RAPPORT_TEST_ISOLE_REGLES_2026_10.md", "Test isolé — règles 2026-10 (niveau évalué, tentatives supplémentaires)")}
ORDER = ["resource", "question", "assessment", "module", "course", "pathway"]
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
            c = content_of(v)
            items.append({"type": t, "doc": v, "content": c, "published": pv, "prev": content_of(prev) if prev else None,
                          "carried": await carried(c) if t == "assessment" else set()})
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
                i.setdefault("before_keys", set()).add((rt, rid))
        i["deps"], i["before"] = deps, before
    for i in items:
        i["cert"] = await credential_regressions(i["doc"]["entity_id"], i["content"]) if i["type"] == "assessment" else []
        for reg in i["cert"]:
            reg["fix"] = cert_providers(items, i, reg["rule"])
            for j in reg["fix"]:
                i["before"].append(f"{j['doc']['entity_id']} v{j['doc']['version']} (certification {reg['credential_id']})")
                i.setdefault("before_keys", set()).add((j["type"], j["doc"]["entity_id"]))
    return topo(items)


async def carried(c: dict) -> set:
    comps = set()
    for q in c.get("questions", []):
        comps |= {w["competency_id"] for w in (await db.questions.find_one({"_id": f"{q['question_id']}@{q.get('version')}"}) or {}).get("competencies", []) if w.get("weight", 0) > 0}
    return comps


def cert_providers(items: List[dict], target: dict, rule: dict) -> List[dict]:
    """Pending assessment (and its pending module raising the level) that would restore a credential rule."""
    need = LEVEL_ORDER.index(rule["min_level"])
    out = []
    for j in items:
        if j is target or j["type"] != "assessment" or j["content"].get("kind") != "graded" or rule["competency_id"] not in j["carried"]:
            continue
        mod = next((m for m in items if m["type"] == "module" and m["doc"]["entity_id"] == j["content"].get("module_id")), None)
        if mod and max((LEVEL_ORDER.index(lv) for lv in mod["content"].get("levels", [])), default=-1) >= need:
            out += [x for x in (j, mod) if x not in out]
    return out


def topo(items: List[dict]) -> List[dict]:
    key = lambda i: (i["type"], i["doc"]["entity_id"])  # noqa: E731
    keys = {key(i) for i in items}
    done, out = set(), []
    while len(out) < len(items):
        nxt = next((i for i in items if key(i) not in done and not ((i.get("before_keys") or set()) & keys) - done), None)
        nxt = nxt or next(i for i in items if key(i) not in done)
        done.add(key(nxt))
        out.append(nxt)
    return out


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


async def evaluated_level(c: dict) -> str:
    mv = await db.module_versions.find_one({"entity_id": c.get("module_id"), "version": c.get("module_version")}) or {}
    return sorted(mv.get("levels") or ["?"], key=lambda x: LEVEL_ORDER.index(x) if x in LEVEL_ORDER else -1)[-1]


async def scoring_block(items: List[dict]) -> List[str]:
    out = ["## Barème et règles"]
    for i in items:
        if i["type"] != "assessment":
            continue
        c = i["content"]
        if c.get("kind") != "graded":
            out += [f"### {i['doc']['entity_id']} v{i['doc']['version']}",
                    "- Quiz formatif : non noté (aucun seuil), aucun acquis ni aucune preuve de certification ; sa publication s'applique à tous les modules qui le référencent."]
            continue
        weights = {}
        for q in c.get("questions", []):
            qd = await db.questions.find_one({"question_id": q["question_id"], "version": q.get("version")}) or {}
            for w in qd.get("competencies", []):
                weights[w["competency_id"]] = weights.get(w["competency_id"], 0) + w["weight"]
        mod = next((m for m in items if m["type"] == "module" and m["doc"]["entity_id"] == c.get("module_id")), None)
        if mod:
            level, mod_label = (mod["content"].get("levels") or ["?"])[-1], f"après publication de {c.get('module_id')} v{mod['doc']['version']}"
        else:
            pv = await published_version("module", c.get("module_id"))
            mv = await db.module_versions.find_one({"entity_id": c.get("module_id"), "version": pv}) or {}
            level, mod_label = (sorted(mv.get("levels") or ["?"], key=lambda x: LEVEL_ORDER.index(x) if x in LEVEL_ORDER else -1))[-1], f"{c.get('module_id')} v{pv} publiée"
        out += [f"### {i['doc']['entity_id']} v{i['doc']['version']}",
                f"- Seuil de réussite : {round(c.get('pass_threshold', 0) * 100)} % du nombre de questions ({len(c.get('questions', []))} questions) ; tentatives : {c.get('max_attempts')}.",
                "- Correction tout-ou-rien par question, choix multiples compris : une question n'est juste que si l'ensemble coché est exactement l'ensemble attendu.",
                "- Acquis : " + "; ".join(f"{k} pondéré sur {v} points, acquis si ≥ {round(ATTAIN_THRESHOLD * 100)} %" for k, v in weights.items())
                + ", calculé uniquement pour une tentative réussie.",
                f"- Niveau de l'acquis (comportement actuel) : niveau maximal de la version de {c.get('module_id')} publiée au moment où la tentative réussie est enregistrée "
                f"({mod_label} : {level}). Ce niveau ne dépend pas de la version de l'évaluation passée, et la tentative n'enregistre pas la version du module (règle en cours de clarification).",
                (f"- Niveau évalué : {await evaluated_level(c)} ({c.get('module_id')} v{c['module_version']}) — règle cible, active seulement avec l'interrupteur CASA_LEVEL_FROM_ASSESSMENT_MODULE_VERSION "
                 "(désactivé en préproduction) : figé par la version de module de l'évaluation, sans hausse rétroactive." if c.get("module_version") else
                 "- Niveau évalué : version de module non renseignée (publication refusée quand la règle cible est active)."),
                "- Tentatives comptées par évaluation, toutes versions confondues : les tentatives déjà faites sur une version antérieure restent comptées et conservées ; acquis existants conservés sans recalcul."]
    for m in items:
        if m["type"] == "module":
            rule = m["content"].get("completion_rule")
            out.append(f"- Règle de fin de {m['doc']['entity_id']} v{m['doc']['version']} : "
                       + ("ressources lues ET quiz noté réussi." if rule != "resources" else "ressources lues.") + f" (completion_rule = {rule}) — complétions existantes conservées, sans recalcul.")
    return out


def load_baseline() -> Optional[dict]:
    files = sorted(BASELINES.glob("*.json"))
    return json.loads(files[-1].read_text()) if files else None


def since_baseline(i: dict, base: Optional[dict]) -> List[str]:
    if not base:
        return []
    title = f"**Changements depuis l'{base['label']}**"
    prev = next((b for b in base["items"] if (b["type"], b["entity_id"], b["version"]) == (i["type"], i["doc"]["entity_id"], i["doc"]["version"])), None)
    if prev is None:
        return [title, "- Nouvel élément depuis cet export.", ""]
    keys = sorted(set(prev["content"]) | set(i["content"]))
    lines = [f"- {k} : {full(prev['content'].get(k))} → {full(i['content'].get(k))}" for k in keys if prev["content"].get(k) != i["content"].get(k)]
    return [title] + (lines or ["- Aucun changement."]) + [""]


async def build_markdown() -> str:
    items = await collect()
    base = load_baseline()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    md = ["# Document de relecture — préproduction — aucune publication", "", f"Généré le {now} depuis la base, en lecture seule. {len(items)} élément(s) en brouillon ou en relecture.", ""]
    md += ["## Ordre de publication"] + [f"{n}. {TYPES[i['type']]['label']} {i['doc']['entity_id']} v{i['doc']['version']}" for n, i in enumerate(items, 1)] + [""]
    crit = [i for i in items if i["cert"]]
    if crit:
        md += ["## Dépendances critiques (certifications)"]
        for i in crit:
            for reg in i["cert"]:
                fix = ", ".join(f"{j['doc']['entity_id']} v{j['doc']['version']}" for j in reg["fix"]) or "aucun brouillon ne la rétablit"
                md.append(f"- **{i['doc']['entity_id']} v{i['doc']['version']}** publié avant {fix} rendrait **{reg['credential_id']}** impossible à obtenir "
                          f"(règle {reg['rule']['id']} : {reg['rule']['competency_id']} niveau {reg['rule']['min_level']}). "
                          "Le contrôle de publication refuse cette publication tant que la règle ne serait plus atteignable.")
        md.append("")
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
        md += since_baseline(i, base)
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


def to_pdf(md: str, footer: str = "Document de relecture — préproduction — aucune publication") -> bytes:
    base = ParagraphStyle("b", fontName="Inter", fontSize=9, leading=13)
    styles = {"# ": ParagraphStyle("h1", parent=base, fontName="Inter-SemiBold", fontSize=15, leading=19, spaceAfter=6),
              "## ": ParagraphStyle("h2", parent=base, fontName="Inter-SemiBold", fontSize=12, leading=16, spaceBefore=10, spaceAfter=4),
              "### ": ParagraphStyle("h3", parent=base, fontName="Inter-SemiBold", fontSize=10, leading=14, spaceBefore=6)}
    flow = []
    for line in md.split("\n"):
        if not line.strip():
            flow.append(Spacer(1, 4))
            continue
        if line.startswith("```") or (line.startswith("|") and set(line) <= set("|-: ")):
            continue
        if line.startswith("|"):
            line = " · ".join(c.strip() for c in line.strip("|").split("|"))
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

    def on_page(canvas, doc):
        canvas.setFont("Inter", 7)
        canvas.drawString(18 * mm, 10 * mm, f"{footer} — page {doc.page}")
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                      title="File de relecture — CASA AI Academy").build(flow, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


@router.get("/admin/reports")
async def list_reports(user: User = Depends(require_roles("admin"))):
    return [{"id": k, "title": t, "available": (MEMORY / f).exists()} for k, (f, t) in REPORTS.items()]


@router.get("/admin/reports/{rid}")
async def get_report(rid: str, format: str = Query("md", pattern="^(md|pdf)$"), user: User = Depends(require_roles("admin"))):
    if rid not in REPORTS or not (MEMORY / REPORTS[rid][0]).exists():
        raise HTTPException(404, "Rapport introuvable")
    md = (MEMORY / REPORTS[rid][0]).read_text()
    name = REPORTS[rid][0].rsplit(".", 1)[0].lower().replace("_", "-")
    if format == "pdf":
        return Response(to_pdf(md, "Rapport — préproduction"), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name}.pdf"'})
    return Response(md, media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{name}.md"'})


@router.get("/admin/review-queue/export")
async def export_review_queue(format: str = Query("md", pattern="^(md|pdf)$"), user: User = Depends(require_roles("admin"))):
    md = await build_markdown()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    if format == "pdf":
        return Response(to_pdf(md), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="file-de-relecture-{stamp}.pdf"'})
    return Response(md, media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="file-de-relecture-{stamp}.md"'})
