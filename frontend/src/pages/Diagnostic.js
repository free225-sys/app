import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { http, useApi } from "@/lib/api";
import { DIAG_STORE_KEY, useAuth } from "@/lib/auth";
import { BTN_PRIMARY, BTN_SECONDARY, Container, ErrorState, LINK_ARROW, Loading, PageHeader } from "@/components/common";
import { QuestionField } from "@/components/learn/QuestionField";

const Result = ({ r, user, onRestart }) => (
  <section className="casa-fade border border-[#14243c]/20 bg-white p-6 sm:p-8" aria-labelledby="diag-result-title" role="status" data-testid="diagnostic-result">
    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#147c77]">Votre résultat</p>
    <h2 id="diag-result-title" className="mt-3 text-3xl font-semibold tracking-tight" data-testid="diagnostic-profile">Entrée {r.profile_name}</h2>
    <p className="mt-3 text-base leading-relaxed">{r.message}</p>
    <dl className="mt-6 grid gap-px border border-[#e5e9ef] bg-[#e5e9ef] text-sm sm:grid-cols-3">
      <div className="bg-[#f7f8fa] px-4 py-3"><dt className="text-xs text-[#627086]">Connaissances</dt><dd className="font-semibold" data-testid="diagnostic-knowledge">{r.knowledge_score}/{r.knowledge_max}</dd></div>
      <div className="bg-[#f7f8fa] px-4 py-3"><dt className="text-xs text-[#627086]">Niveau estimé</dt><dd className="font-mono font-semibold">{r.estimated_level}</dd></div>
      <div className="bg-[#f7f8fa] px-4 py-3"><dt className="text-xs text-[#627086]">Cours recommandé</dt><dd className="font-semibold">{r.course_id}</dd></div>
    </dl>
    <div className="mt-8 flex flex-col gap-3 sm:flex-row">
      {r.preparatory_course_id && (
        <Link to={`/courses/${r.preparatory_course_id}`} className={BTN_PRIMARY} data-testid="diagnostic-preparatory-link">Commencer par {r.preparatory_course_id} <ArrowRight size={16} aria-hidden="true" /></Link>
      )}
      <Link to={`/courses/${r.course_id}`} className={r.preparatory_course_id ? BTN_SECONDARY : BTN_PRIMARY} data-testid="diagnostic-course-link">
        Voir le cours {r.course_id} {!r.preparatory_course_id && <ArrowRight size={16} aria-hidden="true" />}
      </Link>
    </div>
    <p className="mt-6 text-sm text-[#505e75]" data-testid="diagnostic-saved-note">
      {r.saved ? "Résultat enregistré dans votre espace." : (
        <>Résultat non enregistré. <Link to="/inscription?suite=/espace" className="font-semibold text-[#147c77] underline">Créez un compte</Link> pour le conserver : il sera rattaché automatiquement.</>
      )}
    </p>
    <button type="button" onClick={onRestart} className={`${LINK_ARROW} mt-4`} data-testid="diagnostic-restart">Refaire le test</button>
  </section>
);

export default function Diagnostic() {
  const { user } = useAuth();
  const { data, loading, error } = useApi("/diagnostic");
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    const { data: r } = await http.post("/diagnostic/submit", { answers }).finally(() => setBusy(false));
    if (!r.saved) sessionStorage.setItem(DIAG_STORE_KEY, JSON.stringify(answers));
    setResult(r);
    window.scrollTo({ top: 0 });
  };

  return (
    <div data-testid="diagnostic-page">
      <PageHeader eyebrow="Test de positionnement" title="Huit questions pour trouver votre point d'entrée."
        lead="Deux questions sur vos objectifs, six sur vos connaissances. Sans inscription, environ trois minutes. Vous obtenez une entrée et un cours recommandés." />
      <Container className="pt-10">
        {error && <ErrorState />}
        {loading && <Loading />}
        {result && <Result r={result} user={user} onRestart={() => { setResult(null); setAnswers({}); }} />}
        {data && !result && (
          <form onSubmit={submit} className="max-w-3xl space-y-10" data-testid="diagnostic-form">
            {data.questions.map((q, i) => (
              <QuestionField key={q.question_id} q={q} index={i} total={data.questions.length} value={answers[q.question_id] || []}
                onChange={(v) => setAnswers({ ...answers, [q.question_id]: v })} />
            ))}
            <div className="border-t border-[#e5e9ef] pt-6">
              <button type="submit" className={BTN_PRIMARY} disabled={busy || Object.keys(answers).length < data.questions.length} data-testid="diagnostic-submit-button">
                {busy ? "Analyse…" : "Obtenir ma recommandation"}
              </button>
            </div>
          </form>
        )}
      </Container>
    </div>
  );
}
