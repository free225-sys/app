import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { downloadFile, http, useApi } from "@/lib/api";
import { Navigate } from "react-router-dom";
import { RequireAuth, formatApiError, isAdmin, useAuth } from "@/lib/auth";
import { BTN_PRIMARY, BTN_SECONDARY, ErrorState, Loading } from "@/components/common";
import { Review, Rubric, SubmissionStatus } from "@/components/learn/ProjectPanel";

const GradeForm = ({ s, rubric, onDone }) => {
  const [scores, setScores] = useState({});
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const max = Math.max(...rubric.levels.map((l) => l.score));
  const total = rubric.criteria.reduce((a, c) => a + c.weight * max, 0);
  const complete = rubric.criteria.every((c) => scores[c.id] !== undefined);
  const percent = complete ? rubric.criteria.reduce((a, c) => a + c.weight * scores[c.id], 0) / total : null;
  const send = async (decision) => {
    setError("");
    try {
      await http.post(`/evaluation/submissions/${s.id}/review`, { scores, comment, decision });
      onDone();
    } catch (e) {
      setError(formatApiError(e));
    }
  };
  return (
    <div className="mt-6 space-y-5" data-testid={`grade-form-${s.id}`}>
      {rubric.criteria.map((c) => (
        <fieldset key={c.id}>
          <legend className="text-sm font-semibold">{c.label} <span className="font-mono text-xs text-[#627086]">×{c.weight}</span></legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {rubric.levels.map((l) => (
              <label key={l.score} className={`cursor-pointer border px-3 py-1.5 text-xs ${scores[c.id] === l.score ? "border-[#147c77] bg-[#eef5f3] font-semibold" : "border-[#e5e9ef] bg-white"}`} data-testid={`grade-${s.id}-${c.id}-${l.score}`}>
                <input type="radio" name={`${s.id}-${c.id}`} className="sr-only" checked={scores[c.id] === l.score} onChange={() => setScores({ ...scores, [c.id]: l.score })} />
                {l.score} · {l.label}
              </label>
            ))}
          </div>
        </fieldset>
      ))}
      <div>
        <label htmlFor={`comment-${s.id}`} className="text-sm font-semibold">Commentaire pour l'apprenant</label>
        <textarea id={`comment-${s.id}`} rows={4} value={comment} onChange={(e) => setComment(e.target.value)} className="mt-2 w-full border border-[#e5e9ef] bg-white px-3 py-2 text-sm" data-testid={`grade-comment-${s.id}`} />
      </div>
      <p className="text-sm" data-testid={`grade-percent-${s.id}`}>Score pondéré : <span className="font-mono font-semibold">{percent == null ? "—" : `${Math.round(percent * 100)} %`}</span> (seuil {Math.round(rubric.pass_threshold * 100)} %)</p>
      {error && <p role="alert" className="border-l-2 border-[#A04444] bg-[#FBECEC] px-4 py-3 text-sm" data-testid={`grade-error-${s.id}`}>{error}</p>}
      <div className="flex flex-wrap gap-3">
        <button type="button" className={BTN_PRIMARY} disabled={!complete || comment.trim().length < 10} onClick={() => send("validated")} data-testid={`grade-validate-${s.id}`}>Valider le projet</button>
        <button type="button" className={BTN_SECONDARY} disabled={!complete || comment.trim().length < 10} onClick={() => send("rejected")} data-testid={`grade-reject-${s.id}`}>Rejeter</button>
      </div>
    </div>
  );
};

export function EvaluationPanel() {
  const { data: rubric } = useApi("/projects/M16/rubric");
  const [status, setStatus] = useState("submitted");
  const [subs, setSubs] = useState(null);
  const [error, setError] = useState(null);
  const load = () => http.get("/evaluation/submissions", { params: status ? { status } : {} }).then((r) => setSubs(r.data)).catch(setError);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { setSubs(null); load(); }, [status]);
  if (error) return <ErrorState message={formatApiError(error)} />;
  return (
    <section aria-labelledby="evaluation-title" data-testid="evaluation-page">
      <h2 id="evaluation-title" className="text-2xl font-semibold tracking-tight">Projets à évaluer (M16)</h2>
      <p className="mt-2 max-w-[68ch] text-sm text-[#505e75]">Notez chaque critère de la grille, rédigez un commentaire, puis validez ou rejetez. Un projet validé crée une preuve de compétence de type « projet ».</p>
      <div className="mt-8">
        <div className="flex gap-6 border-b border-[#e5e9ef]" role="tablist" aria-label="Filtrer les soumissions">
          {[["submitted", "En attente"], ["validated", "Validés"], ["rejected", "Rejetés"], ["", "Tous"]].map(([k, l]) => (
            <button key={k || "all"} type="button" role="tab" aria-selected={status === k} onClick={() => setStatus(k)}
              className={`-mb-px border-b-2 pb-3 text-sm font-semibold ${status === k ? "border-[#147c77]" : "border-transparent text-[#627086]"}`} data-testid={`evaluation-tab-${k || "all"}`}>{l}</button>
          ))}
        </div>
        {!subs || !rubric ? <Loading /> : subs.length === 0 ? (
          <p className="mt-8 text-sm text-[#505e75]" data-testid="evaluation-empty">Aucune soumission dans cette catégorie.</p>
        ) : (
          <ul className="mt-8 space-y-6">
            {subs.map((s) => (
              <li key={s.id} className="border border-[#e5e9ef] bg-white p-6" data-testid={`evaluation-submission-${s.id}`}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-lg font-semibold">{s.title}</p>
                    <p className="text-xs text-[#627086]">{s.learner.first_name} {s.learner.last_name} · {s.learner.email} · module {s.module_id} · {new Date(s.submitted_at).toLocaleDateString("fr-FR")}</p>
                  </div>
                  <SubmissionStatus status={s.status} />
                </div>
                <p className="mt-4 whitespace-pre-line text-sm leading-relaxed">{s.description}</p>
                {s.file && (
                  <button type="button" onClick={() => downloadFile(`/projects/submissions/${s.id}/file`, s.file.original_filename)} className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-[#147c77] underline" data-testid={`evaluation-download-${s.id}`}>
                    <Download size={14} aria-hidden="true" /> {s.file.original_filename}
                  </button>
                )}
                {s.status === "submitted" ? <GradeForm s={s} rubric={rubric} onDone={load} /> : s.review && <Review s={s} rubric={rubric} />}
              </li>
            ))}
          </ul>
        )}
        {rubric && <details className="mt-12"><summary className="cursor-pointer text-sm font-semibold">Voir la grille publiée</summary><div className="mt-4"><Rubric rubric={rubric} /></div></details>}
      </div>
    </section>
  );
}

const EvaluationGate = () => {
  const { user } = useAuth();
  if (isAdmin(user)) return <Navigate to="/admin?onglet=evaluation" replace />;
  return <ErrorState message="Cette page est réservée à l'administrateur de la plateforme." />;
};

export default function Evaluation() {
  return <RequireAuth><EvaluationGate /></RequireAuth>;
}
