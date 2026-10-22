import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { http } from "@/lib/api";
import { formatApiError } from "@/lib/auth";
import { BTN_PRIMARY, BTN_SECONDARY, ErrorState, Loading } from "@/components/common";
import { QuestionField } from "./QuestionField";

const pct = (v) => `${Math.round((v || 0) * 100)} %`;

const ResultPanel = ({ result, compNames, onRetry }) => {
  const { attempt, status } = result;
  return (
    <div className={`casa-fade border-l-2 px-5 py-5 ${attempt.passed ? "border-[#147c77] bg-[#eef5f3]" : "border-[#A04444] bg-[#FBECEC]"}`} role="status" data-testid="graded-result">
      <div className="flex items-center gap-3">
        {attempt.passed ? <CheckCircle2 className="text-[#147c77]" aria-hidden="true" /> : <XCircle className="text-[#A04444]" aria-hidden="true" />}
        <p className="text-lg font-semibold" data-testid="graded-result-score">
          {attempt.passed ? "Évaluation réussie" : "Seuil non atteint"} — {attempt.score}/{attempt.max_score} ({pct(attempt.percent)})
        </p>
      </div>
      {attempt.level_evaluated && <p className="mt-2 text-sm font-semibold" data-testid="graded-level-evaluated">Niveau évalué : {attempt.level_evaluated} ({attempt.module_id} v{attempt.module_version})</p>}
      <p className="mt-2 text-sm">Tentative {attempt.attempt_number} sur {status.max_attempts}. {status.remaining} tentative{status.remaining > 1 ? "s" : ""} restante{status.remaining > 1 ? "s" : ""}.</p>
      <ul className="mt-4 grid gap-2 sm:grid-cols-2" data-testid="graded-result-competencies">
        {attempt.per_competency.map((c) => (
          <li key={c.competency_id} className="bg-white px-3 py-2 text-sm">
            <span className="font-semibold">{compNames[c.competency_id]}</span> — {c.score}/{c.max} points ({pct(c.percent)})
          </li>
        ))}
      </ul>
      {!attempt.passed && status.remaining > 0 && (
        <button type="button" className={`${BTN_SECONDARY} mt-5 bg-white`} onClick={onRetry} data-testid="graded-retry-button">Nouvelle tentative</button>
      )}
    </div>
  );
};

export const GradedQuiz = ({ moduleId, compNames, onSubmitted }) => {
  const aid = `A-${moduleId}-G`;
  const [quiz, setQuiz] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => http.get(`/assessments/${aid}`).then((r) => setQuiz(r.data)).catch(setLoadError);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [aid]);

  if (loadError) return <ErrorState message={formatApiError(loadError)} />;
  if (!quiz) return <Loading />;

  const details = Object.fromEntries((result?.details || []).map((d) => [d.question_id, d]));
  const status = result?.status || quiz.status;
  const allAnswered = quiz.questions.every((q) => (answers[q.question_id] || []).length);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { data } = await http.post(`/assessments/${aid}/attempts`, { answers });
      setResult(data);
      onSubmitted(data.module_progress);
      window.scrollTo({ top: 0 });
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };
  const retry = () => { setResult(null); setAnswers({}); load(); };

  return (
    <section aria-labelledby="graded-title" data-testid="graded-quiz">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#147c77]">Évaluation notée</p>
      <h2 id="graded-title" className="mt-3 text-3xl font-semibold tracking-tight">Valider le module</h2>
      <dl className="mt-5 grid gap-px border border-[#e5e9ef] bg-[#e5e9ef] text-sm sm:grid-cols-4" data-testid="graded-status">
        {[["Questions", quiz.question_count], ["Seuil de réussite", pct(quiz.pass_threshold)], ["Tentatives utilisées", `${status.attempts_used}/${status.max_attempts}`],
          ["Meilleur score", status.best_percent == null ? "—" : pct(status.best_percent)]].map(([k, v]) => (
          <div key={k} className="bg-white px-4 py-3"><dt className="text-xs text-[#627086]">{k}</dt><dd className="mt-1 font-semibold">{v}</dd></div>
        ))}
      </dl>
      <p className="mt-4 max-w-2xl text-sm leading-relaxed text-[#505e75]">
        Le module est terminé lorsque toutes ses ressources sont marquées comme terminées et que cette évaluation est réussie. Les réponses sont corrigées par le serveur après envoi.
      </p>
      <div className="mt-8">{result && <ResultPanel result={result} compNames={compNames} onRetry={retry} />}</div>
      {!result && status.passed && <p className="mt-6 border-l-2 border-[#147c77] bg-[#eef5f3] px-4 py-3 text-sm" data-testid="graded-already-passed">Vous avez déjà réussi cette évaluation. Une nouvelle tentative reste possible dans la limite autorisée.</p>}
      {status.extra_attempt_available && <p className="mb-3 text-sm font-semibold text-[#147c77]" role="status" data-testid="graded-extra-attempt">1 tentative supplémentaire accordée par l'administrateur</p>}
      {!result && status.remaining === 0 ? (
        <p className="mt-6 flex gap-2 border-l-2 border-[#A0662B] bg-[#FBF1E4] px-4 py-3 text-sm" role="alert" data-testid="graded-no-attempts">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" aria-hidden="true" /> Nombre maximal de tentatives atteint. Contactez votre responsable pédagogique pour un réexamen.
        </p>
      ) : (
        <form onSubmit={submit} className="mt-8 space-y-10" data-testid="graded-form">
          {quiz.questions.map((q, i) => (
            <div key={q.question_id}>
              <QuestionField q={q} index={i} total={quiz.questions.length} value={answers[q.question_id] || []}
                onChange={(v) => setAnswers({ ...answers, [q.question_id]: v })} disabled={!!result} result={details[q.question_id]} compNames={compNames} />
              {details[q.question_id] && <p className="mt-3 text-sm text-[#505e75]" data-testid={`graded-explanation-${q.question_id}`}>{details[q.question_id].explanation}</p>}
            </div>
          ))}
          {!result && (
            <div className="space-y-4 border-t border-[#e5e9ef] pt-6">
              {error && <p role="alert" className="border-l-2 border-[#A04444] bg-[#FBECEC] px-4 py-3 text-sm" data-testid="graded-error">{error}</p>}
              <button type="submit" className={BTN_PRIMARY} disabled={busy || !allAnswered} data-testid="graded-submit-button">
                {busy ? "Correction…" : `Envoyer mes réponses (tentative ${status.attempts_used + 1}/${status.max_attempts})`}
              </button>
              {!allAnswered && <p className="text-xs text-[#627086]">Répondez à toutes les questions pour envoyer.</p>}
            </div>
          )}
        </form>
      )}
    </section>
  );
};
