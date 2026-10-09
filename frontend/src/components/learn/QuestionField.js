export const QuestionField = ({ q, index, total, value, onChange, disabled, result, compNames }) => {
  const multiple = q.type === "multiple";
  const toggle = (id) => onChange(multiple ? (value.includes(id) ? value.filter((v) => v !== id) : [...value, id]) : [id]);
  return (
    <fieldset className="border-t border-[#e5e9ef] pt-6" data-testid={`question-${q.question_id}`}>
      <legend className="float-left w-full">
        <span className="mr-2 font-mono text-sm text-[#627086]">{index + 1}/{total}</span>
        <span className="text-base font-semibold">{q.prompt}</span>
      </legend>
      <div className="clear-both flex flex-wrap gap-2 pt-2 text-xs text-[#627086]">
        {multiple && <span className="font-semibold text-[#14243c]">Plusieurs réponses possibles</span>}
        {compNames && q.competencies.map((c) => <span key={c.competency_id}>· {compNames[c.competency_id]}{c.weight > 1 ? ` ×${c.weight}` : ""}</span>)}
      </div>
      <div className="space-y-2 pt-4">
        {q.options.map((o) => {
          const checked = value.includes(o.id);
          const isRight = result && result.correct_option_ids.includes(o.id);
          const isWrong = result && checked && !isRight;
          return (
            <label key={o.id}
              className={`flex items-start gap-3 border px-4 py-3 text-sm transition-colors duration-200 ${disabled ? "cursor-default" : "cursor-pointer hover:border-[#14243c]/40"} ${
                isRight ? "border-[#147c77] bg-[#eef5f3]" : isWrong ? "border-[#A04444] bg-[#FBECEC]" : checked ? "border-[#14243c] bg-white" : "border-[#e5e9ef] bg-white"}`}
              data-testid={`option-${q.question_id}-${o.id}`}>
              <input type={multiple ? "checkbox" : "radio"} name={q.question_id} value={o.id} checked={checked} disabled={disabled}
                onChange={() => toggle(o.id)} className="mt-0.5 accent-[#147c77]" />
              <span>{o.text}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
};
