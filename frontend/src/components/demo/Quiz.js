import { CheckCircle2, XCircle } from "lucide-react";

const QuizQuestion = ({ q, index, answer, onAnswer }) => {
  const answered = answer !== undefined;
  const correct = answer === q.correct;
  return (
    <fieldset className="border-t border-[#e5e9ef] pt-6" data-testid={`quiz-question-${q.id}`}>
      <legend className="float-left w-full text-base font-semibold">
        <span className="mr-2 font-mono text-sm text-[#627086]">{index + 1}/3</span>
        {q.question}
      </legend>
      <div className="clear-both space-y-2 pt-4">
        {q.options.map((opt, i) => {
          const isRight = answered && i === q.correct;
          const isWrong = answered && i === answer && !correct;
          return (
            <label key={i}
              className={`flex cursor-pointer items-start gap-3 border px-4 py-3 text-sm transition-colors duration-200 ${
                isRight ? "border-[#147c77] bg-[#eef5f3]" : isWrong ? "border-[#A04444] bg-[#FBECEC]" : "border-[#e5e9ef] bg-white hover:border-[#14243c]/40"
              } ${answered ? "cursor-default" : ""}`}
              data-testid={`quiz-option-${q.id}-${i}`}>
              <input type="radio" name={q.id} value={i} checked={answer === i} disabled={answered}
                onChange={() => onAnswer(q.id, i)} className="mt-0.5 accent-[#147c77]" />
              <span>{opt}</span>
            </label>
          );
        })}
      </div>
      {answered && (
        <div role="status" className="casa-fade mt-4 flex gap-3 text-sm" data-testid={`quiz-feedback-${q.id}`}>
          {correct ? <CheckCircle2 size={18} className="shrink-0 text-[#147c77]" aria-hidden="true" /> : <XCircle size={18} className="shrink-0 text-[#A04444]" aria-hidden="true" />}
          <p><strong>{correct ? "Bonne réponse." : "Réponse inexacte."}</strong> {q.feedback}</p>
        </div>
      )}
    </fieldset>
  );
};

export const Quiz = ({ questions, answers, onAnswer, onReset }) => {
  const answeredCount = questions.filter((q) => answers[q.id] !== undefined).length;
  const score = questions.filter((q) => answers[q.id] === q.correct).length;
  return (
    <section aria-labelledby="quiz-title" data-testid="demo-quiz">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#147c77]">Micro-activité</p>
      <h2 id="quiz-title" className="mt-3 text-2xl font-semibold tracking-tight">Trois questions pour vérifier votre compréhension</h2>
      <p className="mt-2 text-sm text-[#505e75]">Activité formative, sans compte : la correction s'affiche immédiatement.</p>
      <div className="mt-8 space-y-8">
        {questions.map((q, i) => <QuizQuestion key={q.id} q={q} index={i} answer={answers[q.id]} onAnswer={onAnswer} />)}
      </div>
      <div className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t border-[#e5e9ef] pt-6">
        <p aria-live="polite" className="text-sm font-semibold" data-testid="quiz-score">
          {answeredCount === questions.length ? `Résultat : ${score}/${questions.length} bonnes réponses.` : `${answeredCount}/${questions.length} questions traitées.`}
        </p>
        {answeredCount > 0 && (
          <button type="button" onClick={onReset} className="text-sm font-semibold text-[#147c77] underline underline-offset-4" data-testid="quiz-reset">
            Recommencer
          </button>
        )}
      </div>
    </section>
  );
};
