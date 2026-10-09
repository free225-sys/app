import { useState } from "react";
import { Download, FileUp } from "lucide-react";
import { downloadFile, http, useApi } from "@/lib/api";
import { formatApiError } from "@/lib/auth";
import { BTN_PRIMARY, Loading } from "@/components/common";

const SUB_LABEL = { submitted: "En attente d'évaluation", validated: "Validé", rejected: "À retravailler" };
const SUB_STYLE = { submitted: "bg-[#EDF3F8] text-[#254a98]", validated: "bg-[#eef5f3] text-[#147c77]", rejected: "bg-[#FBECEC] text-[#7E2828]" };

export const SubmissionStatus = ({ status, testId }) => (
  <span className={`rounded-[10px] px-2 py-0.5 text-xs font-semibold ${SUB_STYLE[status]}`} data-testid={testId}>{SUB_LABEL[status]}</span>
);

export const Rubric = ({ rubric }) => (
  <div className="overflow-x-auto border border-[#e5e9ef] bg-white" data-testid="project-rubric">
    <table className="w-full min-w-[560px] text-left text-sm">
      <thead className="border-b border-[#e5e9ef] text-xs text-[#627086]"><tr><th scope="col" className="px-4 py-3">Critère</th><th scope="col" className="px-4 py-3">Poids</th><th scope="col" className="px-4 py-3">Attendu</th></tr></thead>
      <tbody className="divide-y divide-[#e5e9ef]">
        {rubric.criteria.map((c) => <tr key={c.id}><td className="px-4 py-3 font-semibold">{c.label}</td><td className="px-4 py-3 font-mono">×{c.weight}</td><td className="px-4 py-3 text-[#505e75]">{c.description}</td></tr>)}
      </tbody>
    </table>
    <p className="border-t border-[#e5e9ef] px-4 py-3 text-xs text-[#627086]">Niveaux : {rubric.levels.map((l) => `${l.score} ${l.label}`).join(" · ")} — seuil de validation {Math.round(rubric.pass_threshold * 100)} %.</p>
  </div>
);

export const Review = ({ s, rubric }) => (
  <div className="mt-4 border-l-2 border-[#14243c] bg-white px-4 py-3 text-sm" data-testid={`submission-review-${s.id}`}>
    <p className="font-semibold">Évaluation de {s.review.evaluator_name} — {Math.round(s.review.percent * 100)} %</p>
    {rubric && <ul className="mt-2 grid gap-1 sm:grid-cols-2">{rubric.criteria.map((c) => <li key={c.id} className="text-xs">{c.label} : <span className="font-mono">{s.review.scores[c.id]}/3</span></li>)}</ul>}
    <p className="mt-2 text-[#505e75]">{s.review.comment}</p>
  </div>
);

export const ProjectPanel = ({ moduleId, rubric }) => {
  const { data: subs, loading } = useApi("/learners/me/submissions", { k: moduleId });
  const [list, setList] = useState(null);
  const [form, setForm] = useState({ title: "", description: "" });
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (loading) return <Loading />;
  const mine = (list || subs).filter((s) => s.module_id === moduleId);
  const blocking = mine.find((s) => s.status !== "rejected");

  const submit = async (e) => {
    e.preventDefault();
    if (form.description.trim().length < 50) return setError("La description doit contenir au moins 50 caractères.");
    if (file && file.size > 10 * 1024 * 1024) return setError("Fichier trop volumineux (10 Mo maximum).");
    const fd = new FormData();
    fd.append("title", form.title);
    fd.append("description", form.description);
    if (file) fd.append("file", file);
    setBusy(true);
    setError("");
    try {
      const { data } = await http.post(`/projects/${moduleId}/submissions`, fd);
      setList([data, ...mine]);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-labelledby="project-title" data-testid="project-panel">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#147c77]">Projet appliqué</p>
      <h2 id="project-title" className="mt-3 text-3xl font-semibold tracking-tight">{rubric.title}</h2>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#505e75]">Décrivez votre conception de l'assistant et joignez, si vous le souhaitez, votre dossier (PDF ou DOCX, 10 Mo maximum). Un évaluateur note chaque critère ; un projet validé constitue une preuve de compétence de type « projet ».</p>
      <div className="mt-6"><Rubric rubric={rubric} /></div>
      {mine.length > 0 && (
        <ul className="mt-8 space-y-4" data-testid="project-submissions">
          {mine.map((s) => (
            <li key={s.id} className="border border-[#e5e9ef] bg-[#ffffff] p-5" data-testid={`submission-${s.id}`}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="font-semibold">{s.title}</p>
                <SubmissionStatus status={s.status} testId={`submission-status-${s.id}`} />
              </div>
              <p className="mt-1 text-xs text-[#627086]">Soumis le {new Date(s.submitted_at).toLocaleDateString("fr-FR")}{s.file ? ` · ${s.file.original_filename}` : ""}</p>
              {s.file && (
                <button type="button" onClick={() => downloadFile(`/projects/submissions/${s.id}/file`, s.file.original_filename)} className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-[#147c77] underline" data-testid={`submission-download-${s.id}`}>
                  <Download size={12} aria-hidden="true" /> Télécharger le fichier
                </button>
              )}
              {s.review && <Review s={s} rubric={rubric} />}
            </li>
          ))}
        </ul>
      )}
      {!blocking && (
        <form onSubmit={submit} className="mt-10 space-y-5 border-t border-[#e5e9ef] pt-8" data-testid="project-form">
          <div>
            <label htmlFor="project-title-input" className="text-sm font-semibold">Titre du projet</label>
            <input id="project-title-input" required minLength={3} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="mt-2 w-full border border-[#e5e9ef] bg-white px-3 py-3 text-sm focus:border-[#147c77]" data-testid="project-title-input" />
          </div>
          <div>
            <label htmlFor="project-description-input" className="text-sm font-semibold">Description de la conception</label>
            <textarea id="project-description-input" required rows={8} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="mt-2 w-full border border-[#e5e9ef] bg-white px-3 py-3 text-sm leading-relaxed focus:border-[#147c77]" aria-describedby="project-description-hint" data-testid="project-description-input" />
            <p id="project-description-hint" className="mt-1 text-xs text-[#627086]">50 caractères minimum. Couvrez les cinq critères de la grille.</p>
          </div>
          <div>
            <label htmlFor="project-file-input" className="inline-flex cursor-pointer items-center gap-2 text-sm font-semibold"><FileUp size={16} aria-hidden="true" /> Fichier joint (facultatif)</label>
            <input id="project-file-input" type="file" accept=".pdf,.docx" onChange={(e) => setFile(e.target.files[0] || null)} className="mt-2 block text-sm" data-testid="project-file-input" />
          </div>
          {error && <p role="alert" className="border-l-2 border-[#A04444] bg-[#FBECEC] px-4 py-3 text-sm" data-testid="project-error">{error}</p>}
          <button type="submit" className={BTN_PRIMARY} disabled={busy} data-testid="project-submit-button">{busy ? "Envoi…" : "Soumettre le projet"}</button>
        </form>
      )}
      {blocking && blocking.status === "submitted" && <p className="mt-6 text-sm text-[#505e75]">Votre projet est en cours d'évaluation. Vous serez informé dans votre espace.</p>}
      {mine.some((s) => s.status === "rejected") && !blocking && <p className="mt-4 text-sm text-[#505e75]">Votre précédente soumission est à retravailler : vous pouvez en déposer une nouvelle.</p>}
    </section>
  );
};
