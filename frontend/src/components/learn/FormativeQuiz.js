import { useState } from "react";
import { CheckCircle2, RotateCcw, XCircle } from "lucide-react";
import { http, useApi } from "@/lib/api";
import { BTN_SECONDARY, ErrorState, Loading } from "@/components/common";
import { QuestionField } from "./QuestionField";

const FormativeItem = ({ aid, q, index, total, compNames }) => {
  const [value, setValue] = useState([]);
  const [result, setResult] = useState(null);
  const check = async () => {
    const { data } = await http.post(`/assessments/${aid}/check`, { question_id: q.question_id, answer: value });
    setResult(data);
  };
  return (
    <div>
      <QuestionField q={q} index={index} total={total} value={value} onChange={setValue} disabled={!!result} result={result} compNames={compNames} />
      <div className="mt-4 flex flex-wrap items-start gap-4">
        {!result ? (
          <button type="button" className={BTN_SECONDARY} disabled={!value.length} onClick={check} data-testid={`formative-check-${q.question_id}`}>Vérifier</button>
        ) : (
          <>
            <div role="status" className="casa-fade flex flex-1 gap-3 text-sm" data-testid={`formative-feedback-${q.question_id}`}>
              {result.correct ? <CheckCircle2 size={18} className="shrink-0 text-[#147c77]" aria-hidden="true" /> : <XCircle size={18} className="shrink-0 text-[#A04444]" aria-hidden="true" />}
              <p><strong>{result.correct ? "Bonne réponse." : "Réponse inexacte."}</strong> {result.explanation}</p>
            </div>
            <button type="button" onClick={() => { setValue([]); setResult(null); }} className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#147c77] underline-offset-4 hover:underline" data-testid={`formative-retry-${q.question_id}`}>
              <RotateCcw size={14} aria-hidden="true" /> Réessayer
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export const FormativeQuiz = ({ moduleId, compNames }) => {
  const aid = `A-${moduleId}-F`;
  const { data, loading, error } = useApi(`/assessments/${aid}`);
  if (error) return <ErrorState />;
  if (loading) return <Loading />;
  return (
    <section aria-labelledby="formative-title" data-testid="formative-quiz">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#147c77]">Quiz formatif</p>
      <h2 id="formative-title" className="mt-3 text-3xl font-semibold tracking-tight">S'entraîner, sans enjeu</h2>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#505e75]">Correction et explication immédiates, essais illimités. Ce quiz n'entre pas dans la validation du module.</p>
      <div className="mt-8 space-y-10">
        {data.questions.map((q, i) => <FormativeItem key={q.question_id} aid={aid} q={q} index={i} total={data.questions.length} compNames={compNames} />)}
      </div>
    </section>
  );
};
