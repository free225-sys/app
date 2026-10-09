import { useState } from "react";
import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import { http } from "@/lib/api";
import { formatApiError } from "@/lib/auth";
import { BTN_SMALL, INPUT, LABEL, useOptions } from "./shared";

const EVIDENCE = [{ value: "graded_attempt", label: "Évaluation notée" }, { value: "project", label: "Projet" }];
const RESOURCE_TYPES = ["Texte", "Fiche synthèse", "Exercice guidé", "Étude de cas", "Vidéo", "Fichier"].map((v) => ({ value: v, label: v }));

export function sourceOptions(opts, source, ctx) {
  if (!opts) return [];
  if (Array.isArray(source)) return source;
  if (source === "levels") return opts.levels.map((l) => ({ value: l.id, label: `${l.id} — ${l.name}` }));
  if (source === "stages") return opts.stages.map((s) => ({ value: s.id, label: `${s.code} ${s.name}` }));
  if (["layers", "competencies", "profiles"].includes(source)) return opts[source].map((x) => ({ value: x.id, label: x.name }));
  let items = opts[source] || [];
  if (source === "resource" && ctx?.moduleId) items = items.filter((r) => r.module_id === ctx.moduleId);
  return items.map((x) => ({ value: x.id, label: `${x.id} — ${x.title || ""}` }));
}

export function versionOptions(opts, type, id) {
  const item = (opts?.[type] || []).find((x) => x.id === id);
  return (item?.versions || []).map((v) => ({ value: v.version, label: `v${v.version} (${{ draft: "brouillon", review: "relecture", published: "publiée", retired: "retirée" }[v.status]})` }));
}

const Select = ({ id, value, options, onChange, empty = "— Choisir —", testId, disabled }) => (
  <select id={id} className={INPUT} value={value ?? ""} onChange={(e) => onChange(e.target.value)} data-testid={testId} disabled={disabled}>
    <option value="">{empty}</option>
    {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
  </select>
);

const Chips = ({ value = [], options, onChange, testId, disabled }) => (
  <div className="flex flex-wrap gap-2" role="group" data-testid={testId}>
    {options.map((o) => {
      const on = value.includes(o.value);
      return (
        <button key={o.value} type="button" aria-pressed={on} disabled={disabled} onClick={() => onChange(on ? value.filter((v) => v !== o.value) : [...value, o.value])}
          className={`rounded-[10px] border px-2.5 py-1 text-xs font-medium transition-colors duration-150 ${on ? "border-[#147c77] bg-[#eef5f3] text-[#147c77]" : "border-[#e5e9ef] bg-white text-[#505e75] hover:border-[#14243c]/40"}`}
          data-testid={`${testId}-${o.value}`}>{o.label}</button>
      );
    })}
  </div>
);

const move = (arr, i, d) => {
  const a = [...arr];
  [a[i], a[i + d]] = [a[i + d], a[i]];
  return a;
};

const RowControls = ({ i, n, onMove, onRemove, testId, disabled }) => (
  <div className="flex gap-1">
    <button type="button" className={BTN_SMALL} aria-label="Monter" disabled={disabled || i === 0} onClick={() => onMove(i, -1)} data-testid={`${testId}-up-${i}`}><ArrowUp size={12} aria-hidden="true" /></button>
    <button type="button" className={BTN_SMALL} aria-label="Descendre" disabled={disabled || i === n - 1} onClick={() => onMove(i, 1)} data-testid={`${testId}-down-${i}`}><ArrowDown size={12} aria-hidden="true" /></button>
    <button type="button" className={BTN_SMALL} aria-label="Supprimer" disabled={disabled} onClick={() => onRemove(i)} data-testid={`${testId}-remove-${i}`}><Trash2 size={12} aria-hidden="true" /></button>
  </div>
);

const Ordered = ({ value = [], options, onChange, testId, disabled }) => {
  const [add, setAdd] = useState("");
  const label = (v) => options.find((o) => o.value === v)?.label || v;
  return (
    <div data-testid={testId}>
      <ol className="space-y-1.5">
        {value.map((v, i) => (
          <li key={`${v}-${i}`} className="flex items-center justify-between gap-3 border border-[#e5e9ef] bg-white px-3 py-1.5 text-sm">
            <span><span className="mr-2 font-mono text-xs text-[#627086]">{i + 1}.</span>{label(v)}</span>
            <RowControls i={i} n={value.length} disabled={disabled} testId={testId} onMove={(j, d) => onChange(move(value, j, d))} onRemove={(j) => onChange(value.filter((_, k) => k !== j))} />
          </li>
        ))}
      </ol>
      {!disabled && (
        <div className="mt-2 flex gap-2">
          <Select value={add} options={options.filter((o) => !value.includes(o.value))} onChange={setAdd} empty="— Ajouter —" testId={`${testId}-add-select`} />
          <button type="button" className={BTN_SMALL} disabled={!add} onClick={() => { onChange([...value, add]); setAdd(""); }} data-testid={`${testId}-add`}><Plus size={12} aria-hidden="true" />Ajouter</button>
        </div>
      )}
    </div>
  );
};

const Cell = ({ col, row, onChange, opts, testId, disabled }) => {
  const v = row[col.key];
  if (col.kind === "checkbox") return <input type="checkbox" checked={!!v} disabled={disabled} onChange={(e) => onChange(e.target.checked)} aria-label={col.label} data-testid={testId} />;
  if (col.kind === "number") return <input type="number" step="any" className={INPUT} value={v ?? ""} disabled={disabled} onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))} aria-label={col.label} data-testid={testId} />;
  if (col.kind === "textarea") return <textarea rows={3} className={INPUT} value={v ?? ""} disabled={disabled} onChange={(e) => onChange(e.target.value)} aria-label={col.label} data-testid={testId} />;
  if (col.kind === "select") return <Select value={v} disabled={disabled} options={sourceOptions(opts, col.source)} onChange={onChange} testId={testId} />;
  if (col.kind === "version") return <Select value={v} disabled={disabled} options={versionOptions(opts, col.type, row[col.ref])} onChange={(x) => onChange(x ? Number(x) : "")} empty="Version publiée courante" testId={testId} />;
  if (col.kind === "chips") return <Chips value={v || []} disabled={disabled} options={sourceOptions(opts, col.source)} onChange={onChange} testId={testId} />;
  return <input className={INPUT} value={v ?? ""} disabled={disabled} onChange={(e) => onChange(e.target.value)} aria-label={col.label} data-testid={testId} />;
};

const Rows = ({ value = [], columns, onChange, testId, disabled }) => {
  const opts = useOptions();
  const set = (i, key, v) => onChange(value.map((r, k) => (k === i ? { ...r, [key]: v } : r)));
  return (
    <div className="space-y-3" data-testid={testId}>
      {value.map((row, i) => (
        <div key={i} className="border border-[#e5e9ef] bg-white p-3">
          <div className="grid gap-3 sm:grid-cols-2">
            {columns.map((c) => (
              <div key={c.key} className={c.kind === "textarea" || c.kind === "chips" ? "sm:col-span-2" : ""}>
                <span className="mb-1 block text-xs text-[#627086]">{c.label}</span>
                <Cell col={c} row={row} opts={opts} disabled={disabled} onChange={(v) => set(i, c.key, v)} testId={`${testId}-${i}-${c.key}`} />
              </div>
            ))}
          </div>
          <div className="mt-2 flex justify-end"><RowControls i={i} n={value.length} disabled={disabled} testId={testId} onMove={(j, d) => onChange(move(value, j, d))} onRemove={(j) => onChange(value.filter((_, k) => k !== j))} /></div>
        </div>
      ))}
      {!disabled && <button type="button" className={BTN_SMALL} onClick={() => onChange([...value, {}])} data-testid={`${testId}-add`}><Plus size={12} aria-hidden="true" />Ajouter une ligne</button>}
    </div>
  );
};

const FileInput = ({ value, onChange, testId, disabled }) => {
  const [msg, setMsg] = useState("");
  const upload = async (file) => {
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await http.post("/admin/files", fd);
      onChange(data);
      setMsg("Fichier téléversé.");
    } catch (e) {
      setMsg(formatApiError(e));
    }
  };
  return (
    <div data-testid={testId}>
      {value?.original_filename && <p className="mb-2 text-sm">Fichier actuel : <span className="font-mono">{value.original_filename}</span></p>}
      {!disabled && <input type="file" accept=".pdf,.docx" onChange={(e) => e.target.files[0] && upload(e.target.files[0])} className="text-sm" data-testid={`${testId}-input`} />}
      {msg && <p role="status" className="mt-1 text-xs">{msg}</p>}
    </div>
  );
};

export function FieldInput({ f, content, setContent, entityId, disabled }) {
  const opts = useOptions();
  const value = f.get ? f.get(content) : content[f.key];
  const onChange = (v) => setContent(f.set ? f.set(content, v) : { ...content, [f.key]: v });
  const testId = `field-${f.key}`;
  const id = `fld-${f.key}`;
  const ctx = { moduleId: content.module_id && f.key !== "resource_ids" ? content.module_id : entityId };
  let input;
  switch (f.kind) {
    case "textarea": input = <textarea id={id} rows={4} className={INPUT} value={value ?? ""} disabled={disabled} onChange={(e) => onChange(e.target.value)} data-testid={testId} />; break;
    case "number": input = <input id={id} type="number" step="any" className={INPUT} value={value ?? ""} disabled={disabled} onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))} data-testid={testId} />; break;
    case "select": input = <Select id={id} value={value} disabled={disabled} options={sourceOptions(opts, f.source)} onChange={onChange} testId={testId} />; break;
    case "chips": input = <Chips value={value || []} disabled={disabled} options={sourceOptions(opts, f.source, ctx)} onChange={onChange} testId={testId} />; break;
    case "lines": input = <textarea id={id} rows={4} className={INPUT} value={(value || []).join("\n")} disabled={disabled} onChange={(e) => onChange(e.target.value.split("\n"))} data-testid={testId} />; break;
    case "ordered": input = <Ordered value={value || []} disabled={disabled} options={sourceOptions(opts, f.source, ctx)} onChange={onChange} testId={testId} />; break;
    case "rows": input = <Rows value={value || []} disabled={disabled} columns={f.columns} onChange={onChange} testId={testId} />; break;
    case "levelsmap": input = (
      <div className="space-y-2" data-testid={testId}>
        {["L0", "L1", "L2", "L3", "L4"].map((l) => (
          <label key={l} className="flex items-start gap-3 text-sm"><span className="mt-2 w-8 font-mono text-xs">{l}</span>
            <textarea rows={2} className={INPUT} value={(value || {})[l] || ""} disabled={disabled} onChange={(e) => onChange({ ...(value || {}), [l]: e.target.value })} data-testid={`${testId}-${l}`} /></label>
        ))}
      </div>); break;
    case "file": input = <FileInput value={value} disabled={disabled} onChange={onChange} testId={testId} />; break;
    default: input = <input id={id} className={INPUT} value={value ?? ""} disabled={disabled} onChange={(e) => onChange(e.target.value)} data-testid={testId} />;
  }
  const isGroup = ["chips", "ordered", "rows", "levelsmap", "file"].includes(f.kind);
  return (
    <div className={f.wide ? "sm:col-span-2" : ""}>
      {isGroup ? <p className={LABEL}>{f.label}</p> : <label htmlFor={id} className={LABEL}>{f.label}</label>}
      {f.help && <p className="mt-1 text-xs text-[#627086]">{f.help}</p>}
      <div className="mt-2">{input}</div>
    </div>
  );
}

const W = { wide: true };
export const FIELDS = {
  concept: [
    { key: "name", label: "Nom" }, { key: "short", label: "Définition courte" },
    { key: "definition", label: "Définition", kind: "textarea", ...W }, { key: "example", label: "Exemple", kind: "textarea", ...W },
    { key: "stage_ids", label: "Étapes", kind: "chips", source: "stages", ...W },
    { key: "primary_stage", label: "Étape principale", kind: "select", source: "stages", help: "Par défaut : la première étape cochée." },
    { key: "layer_ids", label: "Couches", kind: "chips", source: "layers", ...W },
    { key: "prerequisite_ids", label: "Notions prérequises", kind: "chips", source: "concept", ...W },
    { key: "module_ids", label: "Modules liés", kind: "chips", source: "module", ...W },
    { key: "treatment", label: "Traitement par niveau", kind: "levelsmap", ...W },
  ],
  resource: [
    { key: "module_id", label: "Module", kind: "select", source: "module" }, { key: "title", label: "Titre" },
    { key: "type", label: "Type", kind: "select", source: RESOURCE_TYPES }, { key: "order", label: "Ordre", kind: "number" },
    { key: "duration_min", label: "Durée (min)", kind: "number" }, { key: "video_url", label: "URL vidéo (https://…)", help: "Pour une ressource vidéo : lien d'intégration." },
    { key: "file", label: "Fichier joint (PDF ou DOCX, 10 Mo max.)", kind: "file", ...W },
    { key: "sections", label: "Sections (texte)", kind: "rows", columns: [{ key: "heading", label: "Intertitre" }, { key: "body", label: "Texte (markdown simple)", kind: "textarea" }], ...W },
  ],
  module: [
    { key: "code", label: "Code" }, { key: "title", label: "Titre" }, { key: "summary", label: "Résumé", kind: "textarea", ...W },
    { key: "objectives", label: "Objectifs (un par ligne)", kind: "lines", ...W }, { key: "prerequisites", label: "Prérequis (texte, un par ligne)", kind: "lines", ...W },
    { key: "prerequisite_module_ids", label: "Modules prérequis", kind: "chips", source: "module", ...W },
    { key: "stage_ids", label: "Étapes", kind: "chips", source: "stages", ...W }, { key: "layer_ids", label: "Couches", kind: "chips", source: "layers", ...W },
    { key: "levels", label: "Niveaux", kind: "chips", source: "levels", ...W }, { key: "competency_ids", label: "Compétences", kind: "chips", source: "competencies", ...W },
    { key: "duration_hours", label: "Durée (heures)", kind: "number" },
    { key: "resource_ids", label: "Ressources (ordre de lecture)", kind: "ordered", source: "resource", ...W },
    { key: "assessment_ids", label: "Quiz liés", kind: "chips", source: "assessment", help: "Par convention : A-{module}-F (formatif) et A-{module}-G (noté).", ...W },
  ],
  question: [
    { key: "module_id", label: "Module", kind: "select", source: "module" },
    { key: "type", label: "Type", kind: "select", source: [{ value: "single", label: "Choix unique" }, { value: "multiple", label: "Choix multiple" }] },
    { key: "prompt", label: "Énoncé", kind: "textarea", ...W },
    { key: "options", label: "Options (cochez les bonnes réponses)", kind: "rows", ...W,
      columns: [{ key: "id", label: "Identifiant (a, b…)" }, { key: "text", label: "Texte" }, { key: "correct", label: "Bonne réponse", kind: "checkbox" }],
      get: (c) => (c.options || []).map((o) => ({ ...o, correct: (c.correct || []).includes(o.id) })),
      set: (c, rows) => ({ ...c, options: rows.map(({ id, text }) => ({ id, text })), correct: rows.filter((r) => r.correct).map((r) => r.id) }) },
    { key: "explanation", label: "Explication", kind: "textarea", ...W },
    { key: "competencies", label: "Compétences évaluées (pondération)", kind: "rows", ...W,
      columns: [{ key: "competency_id", label: "Compétence", kind: "select", source: "competencies" }, { key: "weight", label: "Poids", kind: "number" }] },
  ],
  assessment: [
    { key: "code", label: "Code" }, { key: "title", label: "Titre" },
    { key: "kind", label: "Type", kind: "select", source: [{ value: "formative", label: "Formatif" }, { value: "graded", label: "Noté" }, { value: "diagnostic", label: "Diagnostic" }] },
    { key: "module_id", label: "Module", kind: "select", source: "module" },
    { key: "pass_threshold", label: "Seuil de réussite (0 à 1)", kind: "number" }, { key: "max_attempts", label: "Tentatives maximum", kind: "number" },
    { key: "questions", label: "Questions (versions épinglées)", kind: "rows", ...W,
      columns: [{ key: "question_id", label: "Question", kind: "select", source: "question" }, { key: "version", label: "Version", kind: "version", type: "question", ref: "question_id" }] },
  ],
  course: [
    { key: "code", label: "Code" }, { key: "title", label: "Titre" }, { key: "summary", label: "Résumé", kind: "textarea", ...W },
    { key: "profile_id", label: "Profil", kind: "select", source: "profiles" }, { key: "duration_hours", label: "Durée (heures)", kind: "number" },
    { key: "levels", label: "Niveaux", kind: "chips", source: "levels", ...W },
    { key: "modules", label: "Modules (ordre, version épinglée, optionnel)", kind: "rows", ...W,
      help: "Chaque module est épinglé à une version : publier une nouvelle version d'un module ne modifie pas ce cours.",
      columns: [{ key: "module_id", label: "Module", kind: "select", source: "module" }, { key: "version", label: "Version épinglée", kind: "version", type: "module", ref: "module_id" }, { key: "optional", label: "Optionnel", kind: "checkbox" }],
      get: (c) => (c.module_ids || []).map((m) => ({ module_id: m, version: (c.module_pins || {})[m] || "", optional: (c.optional_module_ids || []).includes(m) })),
      set: (c, rows) => ({ ...c, module_ids: rows.map((r) => r.module_id || ""), module_pins: Object.fromEntries(rows.filter((r) => r.module_id).map((r) => [r.module_id, r.version || null])),
        optional_module_ids: rows.filter((r) => r.optional && r.module_id).map((r) => r.module_id) }) },
  ],
  pathway: [
    { key: "code", label: "Code" }, { key: "title", label: "Titre" }, { key: "summary", label: "Résumé", kind: "textarea", ...W },
    { key: "profile_ids", label: "Profils", kind: "chips", source: "profiles", ...W }, { key: "levels", label: "Niveaux", kind: "chips", source: "levels", ...W },
    { key: "pathway_courses", label: "Cours du parcours et règles de passerelle", kind: "rows", ...W,
      columns: [{ key: "course_id", label: "Cours", kind: "select", source: "course" }, { key: "course_version", label: "Version épinglée", kind: "version", type: "course", ref: "course_id" },
        { key: "group", label: "Groupe", kind: "select", source: [{ value: "mandatory", label: "Obligatoire" }, { value: "optional", label: "Optionnel" }] },
        { key: "evidence", label: "Preuves acceptées pour la reconnaissance", kind: "chips", source: EVIDENCE }],
      get: (c) => (c.pathway_courses || []).map((pc) => ({ ...pc, evidence: pc.bridge?.accepted_evidence_types || [] })),
      set: (c, rows) => ({ ...c, pathway_courses: rows.map(({ evidence, ...pc }) => ({ ...pc, bridge: { module_recognition: "same_module_version", accepted_evidence_types: evidence || [] } })) }) },
    { key: "target_competencies", label: "Compétences cibles", kind: "rows", ...W,
      columns: [{ key: "competency_id", label: "Compétence", kind: "select", source: "competencies" }, { key: "level", label: "Niveau requis", kind: "select", source: "levels" }] },
  ],
  credential: [
    { key: "code", label: "Code" }, { key: "title", label: "Titre" }, { key: "summary", label: "Résumé", kind: "textarea", ...W },
    { key: "rules", label: "Règles d'obtention", kind: "rows", ...W,
      columns: [{ key: "id", label: "Identifiant" }, { key: "label", label: "Libellé" },
        { key: "kind", label: "Type de règle", kind: "select", source: [{ value: "competency", label: "Preuve de compétence" }, { value: "assessment_passed", label: "Évaluation notée réussie" }] },
        { key: "assessment_id", label: "Évaluation notée (si règle d'évaluation)", kind: "select", source: "assessment" },
        { key: "competency_id", label: "Compétence", kind: "select", source: "competencies" },
        { key: "min_level", label: "Niveau minimum", kind: "select", source: "levels" }, { key: "module_id", label: "Module", kind: "select", source: "module" },
        { key: "min_score", label: "Score minimum (0 à 1)", kind: "number" }, { key: "evidence_types", label: "Preuves acceptées", kind: "chips", source: EVIDENCE }] },
  ],
};

export const DEFAULTS = {
  concept: { name: "", short: "", definition: "", example: "", treatment: {}, stage_ids: [], layer_ids: [], prerequisite_ids: [], module_ids: [] },
  resource: { module_id: "", title: "", type: "Texte", order: 1, duration_min: 10, sections: [] },
  module: { code: "", title: "", summary: "", objectives: [], prerequisites: [], prerequisite_module_ids: [], layer_ids: [], stage_ids: [], levels: [], competency_ids: [], duration_hours: 1, resource_ids: [] },
  question: { module_id: "", type: "single", prompt: "", options: [{ id: "a", text: "" }, { id: "b", text: "" }], correct: [], explanation: "", competencies: [] },
  assessment: { code: "", title: "", kind: "formative", module_id: "", pass_threshold: 0.7, max_attempts: 3, questions: [] },
  course: { code: "", title: "", summary: "", profile_id: "", levels: [], module_ids: [], module_pins: {}, optional_module_ids: [], duration_hours: 1 },
  pathway: { code: "", title: "", summary: "", profile_ids: [], levels: [], pathway_courses: [], target_competencies: [] },
  credential: { code: "", title: "", summary: "", rules: [] },
};

export const cleanContent = (c) => {
  const out = { ...c };
  if (out.module_ids) out.module_ids = out.module_ids.filter(Boolean);
  if (out.objectives) out.objectives = out.objectives.filter((x) => x.trim());
  if (out.prerequisites) out.prerequisites = out.prerequisites.filter((x) => x.trim());
  if (out.module_id === "") out.module_id = null;
  return out;
};
